import pytest
import traceback

from pos import POS
import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


def wt_test_multi_array_setup(array_list: list):
    """
    Function to setup the Multi array test environment

    array_list : List of dict of array configuration.
    """
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        for array in array_list:
            array_name = array["array_name"]
            buffer_dev = array["buffer_dev"]
            raid_type = array["raid_type"]
            nr_data_drives = array["nr_data_drives"]
            write_back = array["write_back"]

            if len(system_disks) < (nr_data_drives):
                pytest.skip(
                    f"Insufficient disk count {system_disks}. Required \
                                minimum {nr_data_drives}"
                )
            data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
            spare_disk_list = []

            if raid_type.upper() == "NORAID":
                raid_type = "no-raid"

            assert (
                pos.cli.create_array(
                    write_buffer=buffer_dev,
                    data=data_disk_list,
                    spare=spare_disk_list,
                    raid_type=raid_type,
                    array_name=array_name,
                )[0]
                == True
            )

            assert (
                pos.cli.mount_array(array_name=array_name, write_back=write_back)[0]
                == True
            )
        return True
    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False


array1 = [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4),("RAID10",8)]
array2 = [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4),("RAID10",8)]


@pytest.mark.regression
@pytest.mark.parametrize("io_type", ["block", "file"])
@pytest.mark.parametrize("array2_raid, array2_num_disk", array2)
@pytest.mark.parametrize("array1_raid, array1_num_disk", array1)
def test_wt_multi_array_QOS_FIO(
    array1_raid, array1_num_disk, array2_raid, array2_num_disk, io_type
):
    """
    Test Multi-Array of same RAID types mounted in WT mode
    1. Create 256 volumes to utilize total capacity of array
    2. Set QOS Max IOPS and Max BW to 10
    3. Run Write Block IO and File IO and verify QOS throtteling
    """
    logger.info(
        " ==================== Test : test_wt_multi_array_QOS_FIO ================== "
    )
    try:
        array_name1, array_name2 = "array1", "array2"
        mount_point = []

        arrays_raid_type = (array1_raid, array2_raid)
        arrays_num_disk = (array1_num_disk, array2_num_disk)

        array_list = []
        for id, array_name in enumerate((array_name1, array_name2)):
            array_list.append(
                {
                    "array_name": array_name,
                    "buffer_dev": f"uram{id}",
                    "raid_type": arrays_raid_type[id],
                    "nr_data_drives": arrays_num_disk[id],
                    "write_back": False,
                }
            )

        logger.info(f"array_list {array_list}")

        assert wt_test_multi_array_setup(array_list) == True

        nr_volumes = 256
        for id, array_name in enumerate((array_name1, array_name2)):
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_info[array_name].get("size"))
            vol_size = f"{int((array_size / nr_volumes) / (1024 * 1024))}mb"

            assert (
                pos.target_utils.create_volume_multiple(
                    array_name, nr_volumes, "pos_vol", size=vol_size, maxiops=10, bw=10
                )
                == True
            )

            assert pos.cli.list_volume(array_name)

            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            ss_temp_list = pos.target_utils.ss_temp_list
            ss_list = [ss for ss in ss_temp_list if f"subsystem{id + 1}" in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )

        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = f"fio --name=write --ioengine=libaio --rw=write --iodepth=64 \
                    --bs=128k --time_based --runtime=5 --direct=1 --size={vol_size}"

        nr_dev = 8
        for i in range(nr_volumes // nr_dev):

            nvme_dev_list = pos.client.nvme_list_out[i * nr_dev : (i + 1) * nr_dev]

            if io_type == "file":
                assert pos.client.create_File_system(nvme_dev_list, fs_format="xfs")
                out, mount_point = pos.client.mount_FS(nvme_dev_list)
                assert out == True
                device_list = mount_point
                io_mode = False  # Set False this to File IO
            else:
                device_list = nvme_dev_list
                io_mode = True  # Set False this to Block IO

            assert (
                pos.client.fio_generic_runner(
                    device_list, IO_mode=io_mode, fio_user_data=fio_cmd
                )[0]
                == True
            )

            fio_write = pos.client.fio_par_out["write"]
            logger.info(f"FIO write out {fio_write}")

            if io_type == "file":
                assert pos.client.unmount_FS(mount_point) == True

            qos_data = {"max_iops": 10, "max_bw": 10}
            fio_out = {}

            fio_out["iops"] = fio_write["iops"]
            fio_out["bw"] = fio_write["bw"] / 1000  # Conver to MB

            assert pos.client.fio_verify_qos(qos_data, fio_out, nr_dev) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        if io_type == "file":
            assert pos.client.unmount_FS(mount_point) == True
        pos.exit_handler(expected=False)
