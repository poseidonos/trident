import pytest
import traceback

from common_libs import *
import logger

logger = logger.get_logger(__name__)

array = ["RAID5"]
@pytest.mark.regression
@pytest.mark.parametrize("array_raid", array)
def test_hetero_multi_array_telemetry(array_fixture, array_raid):
    """
    Test to create two RAID5 (Default) arrays with 3 (Default) hetero devices.
    Create and mount 100 volumes from each array. Start Telemetry. 
    Run Block IO for 5 minutes. Stop Telemery.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_telemetry ================== "
    )
    try:
        pos = array_fixture
        repeat_ops = 5
        num_array = 2
        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list
        for counter in range(repeat_ops):
            logger.info(f"Start of {counter+1}/{repeat_ops} Execution!")
            for array_index in range(num_array):
                data_disk_req = {'mix': 2,
                                 'any': (RAID_MIN_DISK_REQ_DICT[array_raid] - 2) }
                assert create_hetero_array(pos, array_raid, data_disk_req, 
                                           array_index=array_index, 
                                           array_mount=True, array_info=True) == True

            assert volume_create_and_mount_multiple(pos, num_volumes=100) == True

            assert pos.cli.telemetry_start()[0] == True

            assert vol_connect_and_run_random_io(pos, subs_list, 
                                                 time_based=True, run_time='5m') == True

            assert pos.cli.telemetry_stop()[0] == True

            assert array_unmount_and_delete(pos) == True

            logger.info(f"End of {counter+1}/{repeat_ops} Execution!")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
