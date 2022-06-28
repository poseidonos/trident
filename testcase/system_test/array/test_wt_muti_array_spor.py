import pytest
import traceback

from pos import POS
import logger
import random
import time
import pprint

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("wt_array.json")
    data_dict = pos.data_dict
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
                pytest.skip(f"Insufficient disk count {system_disks}. Required \
                                minimum {nr_data_drives}")
            data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
            spare_disk_list = []

            if raid_type.upper() == "NORAID":
                raid_type = "no-raid"

            assert pos.cli.create_array(write_buffer=buffer_dev, data=data_disk_list,
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name, 
                                        write_back=write_back)[0] == True
        return True
    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False


array1 = [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)]
array2 = [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)]

@pytest.mark.regression
@pytest.mark.parametrize("writeback" , [True, False])
@pytest.mark.parametrize("array2", array2)
@pytest.mark.parametrize("array1", array1)
def test_wt_multi_array_FIO_SPOR_NPOR(array1, array2, writeback):
    """
    Test Multi-Array in all RAID combination with WT/WB mount.
    1. Run Write Block IO for an hour.
    2. Trigger SPOR
    3. Trigger NPOR
    """
    logger.info(
        " ==================== Test : test_wt_multi_array_FIO_SPOR_NPOR ================== "
    )
    try:
        array_name1 = "array1"
        array_name2 = "array2"

        array_raid_disk = (array1, array2)

        array_list = []
        for id, array_name in enumerate((array_name1, array_name2)):
            array_list.append({
                "array_name": array_name,
                "buffer_dev": f"uram{id}",
                "raid_type": array_raid_disk[id][0],
                "nr_data_drives": array_raid_disk[id][1],
                "write_back": writeback
                }
            )

        assert wt_test_multi_array_setup(array_list) == True

        for id, array_name in enumerate((array_name1, array_name2)):
            assert pos.cli.info_array(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_info[array_name].get("size"))
            vol_size = f"{array_size // (1024 * 1024)}mb"          # Volume Size in MB

            assert pos.target_utils.create_volume_multiple(array_name, 1, 
                                            "pos_vol", size=vol_size) == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            ss_temp_list = pos.target_utils.ss_temp_list
            ss_list = [ss for ss in ss_temp_list if f"subsystem{id + 1}" in ss]
            assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                            volume_list=pos.cli.vols, nqn_list=ss_list) == True

        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss,
                            pos.target_utils.helper.ip_addr[0], "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        fio_cmd = f"fio --name=random_write --ioengine=libaio --rw=randwrite \
            --iodepth=64 --direct=1 --bs=128k --time_based --runtime=3600"

        assert pos.client.fio_generic_runner(nvme_devs,
                                        fio_user_data=fio_cmd)[0] == True

        # Perfrom SPOR
        assert pos.target_utils.Spor() == True

        # Perform NPOR
        assert pos.target_utils.Npor() == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

