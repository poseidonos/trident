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


@pytest.mark.regression
@pytest.mark.parametrize("array_mount", ["NO", "WT", "WB"])
@pytest.mark.parametrize("num_spare_disk", [0, 1, 2, 4])
@pytest.mark.parametrize("num_data_disk", [2, 3, 4, 8, 16, 30, 32])
def test_create_raid6_array(num_data_disk, num_spare_disk, array_mount):
    """
    The purpose of this test is to create RAID 6 array with different data disk and spare disk.
    It includes the positive and negative test.
    Verification: POS CLI - Create Array Mount Array and List Array command.
    """
    logger.info(
        f" ==================== Test : test_create_raid6_array[{num_data_disk}-{num_spare_disk}-{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        exp_res = True

        if num_data_disk < RAID6_MIN_DISKS:
            exp_res = False
        if num_data_disk + num_spare_disk > len(system_disks):
            exp_res = False

        auto_create = False
        assert single_array_data_setup(pos.data_dict, "RAID6", num_data_disk,
                            num_spare_disk, array_mount, auto_create) == True

        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == exp_res

        if exp_res:
            array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
            assert pos.cli.info_array(array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
@pytest.mark.parametrize("array_mount", ["NO", "WT", "WB"])
@pytest.mark.parametrize("num_spare_disk", [0, 1, 2, 4])
@pytest.mark.parametrize("num_data_disk", [2, 3, 4, 8, 16])
def test_auto_create_raid6_array(num_data_disk, num_spare_disk, array_mount):
    """
    The purpose of this test is to create RAID 6 array with different data disk and spare disk.
    It includes the positive and negative test.
    Verification: POS CLI - Create Array Mount Array and List Array command.
    """
    logger.info(
        f" ==================== Test : test_create_raid6_array[{num_data_disk}-{num_spare_disk}-{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        exp_res = True

        if num_data_disk < RAID6_MIN_DISKS:
            exp_res = False
        if num_data_disk + num_spare_disk > len(system_disks):
            exp_res = False

        auto_create = True
        assert single_array_data_setup(pos.data_dict, "RAID6", num_data_disk,
                            num_spare_disk, array_mount, auto_create) == True

        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == exp_res

        if exp_res:
            array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
            assert pos.cli.info_array(array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
@pytest.mark.parametrize("vol_utilize", [50, 100, 105])
@pytest.mark.parametrize("num_volumes", [1, 2, 100, 256, 257])
def test_raid6_array_with_volumes(num_volumes, vol_utilize, array_mount):
    """
    The purpose of this test is to create RAID 6 array with different volumes and utilize its capacity.
    It includes the positive and negative test.
    Verification: POS CLI - Array - Create, Mount, and List: Volume - Create, Mount, List
    """
    logger.info(
       f" ==================== Test : test_raid6_array_volumes[{num_volumes}-{vol_utilize}-{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < RAID6_MIN_DISKS:
            pytest.skip("Less number of data disk")

        auto_create = False
        assert single_array_data_setup(pos.data_dict, "RAID6", RAID6_MIN_DISKS,
                                       0, array_mount, auto_create) == True

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