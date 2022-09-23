import pytest

from pos import POS
from common_raid6_api import *

import logger
logger = logger.get_logger(__name__)

@pytest.fixture(scope="module")
def pos_connection():
    logger.info("========= SETUP MODULE ========")
    pos = POS()

    yield pos

    

    logger.info("========= CLEANUP MODULE ========")
    del pos

@pytest.fixture(scope="function")
def journal_setup_cleanup(pos_connection):
    logger.info("========== SETUP TEST =========")
    pos = pos_connection
    if not pos.target_utils.helper.check_pos_exit():
        assert pos.cli.stop_system()[0] == True

    data_dict = pos.data_dict
    data_dict['system']['phase'] = "true"
    data_dict['subsystem']['phase'] = "true"
    data_dict['device']['phase'] = "true"

    yield pos

    logger.info("========== CLEANUP AFTER TEST =========")

    assert pos_system_restore_stop(pos) == True
    assert pos.pos_conf.restore_config() == True

    logger.info("==========================================")

def pos_bringup(pos):
    try:
        data_dict = pos.data_dict
        data_dict['array']['phase'] = "false"
        data_dict['volume']['phase'] = "false"
        assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

        data_dict['system']['phase'] = "false"
        data_dict['subsystem']['phase'] = "false"
        data_dict['device']['phase'] = "false"
        data_dict['array']['phase'] = "true"
        return True
    except Exception as e:
        logger.error(f"Failed to bringup pos due to {e}")
        return False


# Num of Volumes, IO (Write, Rand Write, Read, Random Read))
jouranl_enable = [True, False]
@pytest.mark.parametrize("jouranl_enable", jouranl_enable)
@pytest.mark.parametrize("raid_type", ARRAY_ALL_RAID_LIST)
def test_raid6_arrays_journal_enable(journal_setup_cleanup, raid_type, jouranl_enable):
    """
    The purpose of this test is to create two arrays and atleast 1 should be RAID 6. 
    Create and mount multiple volumes to each array and utilize its full capacity.  
    Run File IO, Block IO and Mix of File and Block IO.
    Verification: POS CLI, End to End Data Flow, Data Integrity
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_journal_enable[{raid_type}-{jouranl_enable}] ================== "
    )
    pos = journal_setup_cleanup
    try:
        assert pos.pos_conf.journal_state(enable=jouranl_enable,
                                          update_now=True) == True

        assert pos_bringup(pos) == True

        num_vols = 8
        num_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
        arrays_num_disks = (RAID6_MIN_DISKS, num_disk)
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", raid_type), 
                                      arrays_num_disks, (0, 0), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert volume_create_and_mount_multiple(pos, num_vols) == True
        subs_list = pos.target_utils.ss_temp_list

        assert vol_connect_and_run_random_io(pos, subs_list, '50gb') == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
