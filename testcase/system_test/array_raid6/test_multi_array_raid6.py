import pytest

from pos import POS
from common_raid6_api import *

import logger
logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict['array']['phase'] = "false"
    data_dict['volume']['phase'] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos

def setup_function():
    data_dict = pos.data_dict
    if pos.target_utils.helper.check_pos_exit() == True:
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

    data_dict['system']['phase'] = "false"
    data_dict['device']['phase'] = "false"
    data_dict['subsystem']['phase'] = "false"
    data_dict['array']['phase'] = "true"

def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.cli.list_array()[0] == True
    for array_name in pos.cli.array_dict.keys():
        assert pos.cli.info_array(array_name=array_name)[0] == True
        if pos.cli.array_dict[array_name].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.delete_array(array_name=array_name)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


array_list = [("NORAID", 0), ("RAID0", 2), ("RAID5", 3), ("RAID6", 4), ("RAID10", 4)]

@pytest.mark.regression
@pytest.mark.parametrize("array_mount", [("WT", "WT"), ("WB", "WB"), ("WT", "WB"), ("WB", "WT")])
@pytest.mark.parametrize("raid_type, num_disks", array_list)
def test_create_raid6_array_with_all_raids(raid_type, num_disks, array_mount):
    """
    The purpose of this test is to create two arrays. One of them should be RAID 6 always.
    Verification: POS CLI - Create Array Mount Array and List Array command.
                  Multi Array Operability. 
    """
    logger.info(
        f" ==================== Test : test_create_raid6_array_with_others[{raid_type}-{num_disks}-{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        exp_res = True

        arrays_raid_type = ("RAID6", raid_type)
        arrays_num_disks = (RAID6_MIN_DISKS, num_disks)
        arrays_auto_create = (False, False)

        if sum(arrays_num_disks) > len(system_disks):
            exp_res = False

        assert multi_array_data_setup(pos.data_dict, 2, arrays_raid_type, arrays_num_disks,
                                      (0, 0), array_mount,  arrays_auto_create) == True

        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == exp_res

        if exp_res:
            assert pos.cli.list_array()[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("vol_utilize", [50, 100, 105])
@pytest.mark.parametrize("num_volumes", [1, 256, 257])
def test_two_raid6_array_capacity(num_volumes, vol_utilize, array_mount):
    """
    The purpose of this test is to create RAID 6 array with different volumes and utilize its capacity.
    It includes the positive and negative test.
    Verification: POS CLI - Array - Create, Mount, and List: Volume - Create, Mount, List
    """
    logger.info(
        f" ==================== Test : test_create_raid6_array_volumes[{num_volumes}-{vol_utilize}-{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        exp_res = True
        arrays_raid_type = ("RAID6", "RAID6")
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        arrays_auto_create = (False, False)

        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, arrays_raid_type, arrays_num_disks,
                                      (0, 0), array_mount, arrays_auto_create) == True
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert pos.cli.list_array()[0] == True
        array_list = [array_name for array_name in pos.cli.array_dict.keys()]

        assert pos.cli.list_subsystem()[0] == True
        subsyste_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, array_list, vol_utilize,
                                                num_volumes, mount_vols=True,
                                                sbus_list=subsyste_list) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)