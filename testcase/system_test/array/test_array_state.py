import pytest
import traceback
import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize("num_drives", [(0), (1), (2)])
def test_stop_arrray_state(array_fixture, num_drives):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 1
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = "RAID5"
        pos.data_dict["array"]["pos_array"][0]["data_device"] = 4
        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 1
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.array_info(array_name=array_name)[0] == True
        data_list = pos.cli.array_data[array_name]["data_list"]
        spare_list = pos.cli.array_data[array_name]["spare_list"]

        assert pos.target_utils.device_hot_remove(data_list[:num_drives]) == True
        assert pos.cli.array_info(array_name)[0] == True
        array_state = pos.cli.array_data[array_name]["state"]
        array_situation = pos.cli.array_data[array_name]["situation"]
        logger.info(f"Array state : {array_state}, situation : {array_situation}")
        if (num_drives == 0):
            # Array should be in normal state
            assert array_state == "NORMAL" and array_situation == "NORMAL"
        elif (num_drives == 2):
            # Array should be in fault or degraded state as 2 disks are removed
            assert array_state in ["STOP", "BUSY"]
            assert array_situation == ["FAULT", "DEGRADED"]
        elif (num_drives == 1):
            # Array should be in Rebuilding or Normal State
            assert array_state in ["BUSY", "NORMAL"]
            assert array_situation == ["REBUILDING", "NORMAL"]
        else:
            # Set state
            pass

        assert pos.cli.array_addspare(array_name=array_name, 
                                device_name=spare_list[0])[0] == False
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
