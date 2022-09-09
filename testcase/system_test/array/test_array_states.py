import pytest
import traceback


import logger
logger = logger.get_logger(__name__)


def test_setup_function(setup_cleanup_array_function):
    try:
        pos = setup_cleanup_array_function
        global array_name,system_disks,data_disk_list
        array_name = "posarray1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (3):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        spare_disk_list = []
        assert pos.cli.create_array(write_buffer="uram0",data=data_disk_list,spare=spare_disk_list,raid_type="RAID5",array_name=array_name)[0]== True
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        return True
    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False


@pytest.mark.regression
@pytest.mark.parametrize(
    "num_drives",[(0),(1),(2)]
    )
def test_stop_arrray_state(setup_cleanup_array_function, num_drives):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert test_setup_function() == True
        spare_disk_list = [system_disks.pop()]
        assert pos.target_utils.device_hot_remove(data_disk_list[:num_drives]) == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(array_status["state"])
        if (pos.cli.array_info[array_name]["state"] == "NORMAL") and (pos.cli.array_info[array_name]["situation"] == "NORMAL"):
            logger.info("Expected array state mismatch with output{}".format(array_status["state"]))
        elif (pos.cli.array_info[array_name]["state"] == "STOP") and (pos.cli.array_info[array_name]["situation"] == "FAULT"):
            logger.error("Expected array state mismatch with output{}".format(array_status["state"]))
        elif (pos.cli.array_info[array_name]["state"] == "BUSY") and (pos.cli.array_info[array_name]["situation"] == "DEGRADED"):
            assert pos.cli.addspare_array(array_name=array_name,device_name=spare_disk_list[0])[0] == True
            assert pos.cli.array_info[array_name]["situation"] == "REBUILDING"
            logger.info("As expected rebuild in progress")
        else:
            assert 0
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
