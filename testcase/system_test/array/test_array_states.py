import pytest
import traceback
import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression
@pytest.mark.parametrize(
    "num_drives",[(0),(1),(2)]
    )
def test_stop_arrray_state(array_fixture, num_drives):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict['array']['num_array'] = 1
        pos.data_dict['array']['pos_array'][0]["data_device"] = 4
        pos.data_dict['array']['pos_array'][0]["spare_device"] = 1
        assert pos.target_utils.bringupArray(data_dict = pos.data_dict) == True
        assert pos.cli.list_array()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.info_array(array_name = array_name)[0] == True
        data_list = pos.cli.array_info[array_name]['data_list']
        spare_list =  pos.cli.array_info[array_name]['spare_list']
        
        assert pos.target_utils.device_hot_remove(data_list[:num_drives]) == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(array_status["state"])
        if (pos.cli.array_info[array_name]["state"] == "NORMAL") and (pos.cli.array_info[array_name]["situation"] == "NORMAL"):
            logger.info("Expected array state mismatch with output{}".format(array_status["state"]))
        elif (pos.cli.array_info[array_name]["state"] == "STOP") and (pos.cli.array_info[array_name]["situation"] == "FAULT"):
            logger.error("Expected array state mismatch with output{}".format(array_status["state"]))
        elif (pos.cli.array_info[array_name]["state"] == "BUSY") and (pos.cli.array_info[array_name]["situation"] == "DEGRADED"):
            assert pos.cli.addspare_array(array_name=array_name,device_name=spare_list[0])[0] == True
            assert pos.cli.array_info[array_name]["situation"] == "REBUILDING"
            logger.info("As expected rebuild in progress")
       
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
