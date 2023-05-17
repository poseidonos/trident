import pytest
import traceback

from common_libs import *
import logger

logger = logger.get_logger(__name__)

array = ["RAID5"]

@pytest.mark.regression
@pytest.mark.parametrize("array_raid", array)
def test_hetero_multi_array_smart_log(array_fixture, array_raid):
    """
    Test to create two RAID5 (Default) arrays with 3 (Default) hetero devices.
    Create and mount 100 volumes from each array. Trigger GC.
    """
    logger.info(
        " ==================== Test :  test_hetero_multi_array_GC ================== "
    )
    try:
        pos = array_fixture

        num_array = 2
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:num_array]
        for array_index in range(num_array):
            data_disk_req = {'mix': 2,
                             'any': (RAID_MIN_DISK_REQ_DICT[array_raid] - 2) }
            assert create_hetero_array(pos, array_raid, data_disk_req, 
                                       array_index=array_index, 
                                       array_mount=True, array_info=True) == True

        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.array_info(array_name=array_name)[0] == True
            for device in pos.cli.array_data[array_name]["data_list"]:
                assert pos.cli.device_smart_log(devicename=device)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
