import pytest

from pos import POS
import logger
import random
import time


logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("wt_array.json")
    data_dict = pos.data_dict
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
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

    assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives,IO",
    [
        ("no-raid", 1, "Block"),
        ("RAID0", 2, "Block"),
        ("RAID10", 4, "Block"),
        ("RAID10", 2, "Block"),
        ("no-raid", 1, "File"),
        ("RAID0", 2, "File"),
        ("RAID10", 4, "File"),
        ("RAID10", 2, "File"),
    ],
)
def test_wt_multi_array_qos(raid_type, nr_data_drives, IO):

    logger.info(
        " ==================== Test : test_wt_multi_array_qos ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
            res = pos.cli.create_array(
                write_buffer=f"uram{str(index)}",
                array_name=array,
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
            )
            assert res[0] == True
            assert pos.cli.mount_array(array_name=array, write_back=False)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=256, size="10gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            for volname in pos.cli.vols:
                assert pos.cli.create_volume_policy_qos(
                    arrayname=array, volumename=volname, maxiops=10, maxbw=10
                )
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem" in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array,
                    volume_list=pos.cli.vols,
                    nqn_list=[ss_list[index]],
                )
                == True
            )
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        if IO == "File":
            for dev in pos.client.nvme_list_out:
                assert pos.client.create_File_system(dev, fs_format="ext4")
                status, mount_point = pos.client.mount_FS(dev)
                assert status == True

                fio_cmd = "fio --name=Rand_RW  --runtime=300 --ramp_time=60  --ioengine=sync  --iodepth=32 --rw=write --size=1000g bs=32kb --direct=1 --verify=md5"

                status, fio_out = pos.client.fio_generic_runner(
                    mount_point, fio_user_data=fio_cmd, IO_mode=False, run_async=True
                )
                assert status == True
                logger.info(fio_out)

                assert pos.client.unmount_FS(mount_point) == True
                assert pos.client.delete_FS(mount_point) == True

        else:
            fio_out = pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=300",
                run_async=True,
            )
            assert fio_out[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
