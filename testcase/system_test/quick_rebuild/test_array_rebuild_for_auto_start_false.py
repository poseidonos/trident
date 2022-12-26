import pytest

from pos import POS
from common_test_api import *

import logger
logger = logger.get_logger(__name__)

@pytest.fixture(scope="module")
def setup_module():
    logger.info("========= SETUP MODULE ========")
    pos = POS()
    if not pos.target_utils.helper.check_pos_exit():
        assert pos.cli.stop_system()[0] == True
    assert pos.pos_conf.rebuild_auto_start(auto_start=False,
                                           update_now=True) == True

    data_dict = pos.data_dict
    data_dict['array']['phase'] = "false"
    data_dict['volume']['phase'] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    yield pos

    logger.info("========= CLEANUP MODULE ========")
    assert pos_system_restore_stop(pos) == True
    assert pos.pos_conf.restore_config() == True
    del pos

@pytest.fixture(scope="function")
def auto_rebuild_setup_cleanup(setup_module):
    logger.info("========== SETUP TEST =========")
    pos = setup_module
    data_dict = pos.data_dict
    if pos.target_utils.helper.check_pos_exit() == True:
        data_dict['system']['phase'] = "true"
        data_dict['subsystem']['phase'] = "true"
        data_dict['device']['phase'] = "true"
        data_dict['array']['phase'] = "false"
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
    data_dict['system']['phase'] = "false"
    data_dict['subsystem']['phase'] = "false"
    data_dict['device']['phase'] = "false"
    data_dict['array']['phase'] = "true"

    yield pos

    logger.info("========== CLEANUP AFTER TEST =========")

    assert pos_system_restore_stop(pos, client_disconnect=True) == True
    logger.info("==========================================")

test_opr = ["disk_replace_rebuild", "disk_remove", "disk_remove_rebuild"]

@pytest.mark.parametrize("test_operation", test_opr)
def test_array_rebuild_auto_start_disable(auto_rebuild_setup_cleanup, test_operation):
    """
    The purpose of this test is to create RAID5 array with 3 data drive and 1 spare drive. 
    Create and mount 2 multiple volumes to each array and utilize its full capacity.  
    Verification: POS CLI, End to End Data Flow, Data Integrity
    """
    logger.info(
        f" ==================== Test : test_array_rebuild_auto_start_disable[{test_operation}] ================== "
    )
    pos = auto_rebuild_setup_cleanup
    try:
        raid_type = "RAID5"
        num_vols = 2
        num_data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
        num_spare_disk = 1
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < (num_data_disk + num_spare_disk):
            pytest.skip("Less number of system disks")

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       num_data_disk, num_spare_disk,
                                       "WT", False) == True

        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert volume_create_and_mount_multiple(pos, num_vols) == True
        subs_list = pos.target_utils.ss_temp_list

        assert vol_connect_and_run_random_io(pos, subs_list, '100gb') == True

        array_name = pos.data_dict['array']["pos_array"][0]["array_name"]
        assert pos.cli.info_array(array_name=array_name)[0] == True
        data_disk_list = pos.cli.array_info[array_name]["data_list"]

        random.shuffle(data_disk_list)
        selected_disks = data_disk_list[0]

        if test_operation == "disk_replace_rebuild":
            assert pos.cli.replace_drive_array(selected_disks, array_name)[0] == True
            array_situation = "REBUILDING"
        else:
            assert pos.target_utils.device_hot_remove([selected_disks]) == True
            assert pos.target_utils.pci_rescan() == True
            array_situation = "DEGRADED"
        
        time.sleep(2) # Wait 2 seconds and verify the rebuilding should not start
        assert pos.cli.info_array(array_name=array_name)[0] == True
        assert pos.cli.array_info[array_name]["situation"] == array_situation

        if test_operation != "disk_replace_rebuild":
            assert pos.cli.rebuild_array(array_name)[0] == True
            assert pos.target_utils.array_rebuild_wait(array_name=array_name) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

