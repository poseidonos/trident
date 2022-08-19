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
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict['array']['num_array'] = 0
    data_dict['volume']['phase'] = "false"
    array_name = data_dict["array"]["pos_array"][0]["array_name"]
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos



def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
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


def negative_test_setup_function(nr_data_drives: int):
    try:
        global array_name,system_disks,data_disk_list
        array_name = "posarray1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        return True

    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False


@pytest.mark.regression
def test_array_invalid_data_disk(raid_type="RAID5", nr_data_drives=3):
    logger.info(" ==================== Test : test_array_invalid_drives ================== ")
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        system_disks = ["dummy1","dummy2","dummy1"]
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        status = pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )
        assert status[0] == False
        logger.info("As expected testcases failed due to {}".format(status[1]["output"]["Response"]["result"]["status"]["eventName"]))
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_create_array_invalid_commands(raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_create_array_invalid_commands ================== "
    )
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        assert (
            pos.cli.create_array(
                write_buffer="dummy",
                data=data_disk_list,
                spare=None,
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == False
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_less_data_drive(raid_type="RAID5", nr_data_drives=2):
    logger.info(
        " ==================== Test : test_array_less_data_drive ================== "
    )
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        status = pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )
        assert status[0] == False
        logger.info("As expected testcases failed due to {}".format(status[1]["output"]["Response"]["result"]["status"]["eventName"]))
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_add_spare_without_array_mount(raid_type="RAID5", nr_data_drives=3):
    logger.info(" ==================== Test : test_add_spare_without_mount ================== ")
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.addspare_array(array_name=array_name,device_name=spare_disk_list[0])[0] == False
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_mnt_without_arrays(nr_data_drives=3):
    logger.info(" ==================== Test : test_array_cli_wt ================== ")
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        status = pos.cli.mount_array(array_name=array_name, write_back=False)
        assert status[0] == False
        logger.info("As expected testcases failed due to {}".format(status[1]["output"]["Response"]["result"]["status"]["description"]))
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_mnt_vol_stop_arrray_state(raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert pos.target_utils.device_hot_remove(data_disk_list[:2]) == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_info[array_name]["state"] != "STOP":
            logger.error("Expected array state mismatch with output{}".format(array_status["state"]))
            assert 0
        else:
            assert (
                pos.cli.create_volume(
                    array_name=array_name, size="10gb", volumename="vol"
                )[0]
                == False
            )
            logger.info("As expected volume creation failed in array stop state")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)        

@pytest.mark.regression
def test_rename_vol_stop_arrray_state(raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[0]== True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        assert pos.target_utils.device_hot_remove(data_disk_list[:2]) == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_info[array_name]["state"] != "STOP":
            logger.error("Expected array state mismatch with output{}".format(array_status["state"]))
            assert 0
        else:
            assert pos.cli.rename_volume(array_name=array_name,volname=pos.cli.vols[0],new_volname='posvol')[0] == False
            logger.info("As expected volume rename failed in array stop state")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_state_vol_state(raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        assert negative_test_setup_function(nr_data_drives) == True
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_info[array_name]["state"] == "NORMAL":
            assert pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[0]== True
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            assert pos.cli.mount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
            assert pos.cli.unmount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
            logger.info("Expected array state mismatch with output{} and volume mount was sucessful".format(array_status["state"]))
        else:
            assert 0
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


