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
        if pos.cli.array_dict[array_name].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.delete_array(array_name=array_name)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_create_raid6_array(array_mount):
    """
    The purpose of this test is to create RAID 6 array with different data disk and spare disk.
    It includes the positive and negative test.
    Verification: POS CLI - Create Array Mount Array and List Array command.
    """
    logger.info(
        f" ==================== Test : test_create_raid6_array[{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks

        array_disks = [(4, 0), (4, 1), (4, 2), (8, 2), (16, 2), (28,2), (30, 0), (3, 0), (2, 2)]
        for data_disk, spare_disk in array_disks:
            if (data_disk + spare_disk) > len(system_disks):
                logger.warning("Insufficient system disks to test array create")
                continue
            
            exp_res = False if data_disk < RAID6_MIN_DISKS else True

            auto_create = False
            assert single_array_data_setup(pos.data_dict, "RAID6", data_disk,
                                spare_disk, array_mount, auto_create) == True

            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == exp_res

            if exp_res:
                assert array_unmount_and_delete(pos) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_auto_create_raid6_array(array_mount):
    """
    The purpose of this test is to create RAID 6 array with different data disk and spare disk.
    It includes the positive and negative test.
    Verification: POS CLI - Create Array Mount Array and List Array command.
    """
    logger.info(
        f" ==================== Test : test_create_raid6_array[{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks

        array_disks = [(4, 0), (4, 1), (4, 2), (3, 2), (2, 2)]
        for data_disk, spare_disk in array_disks:
            if (data_disk + spare_disk) > len(system_disks):
                logger.warning("Insufficient system disks to test array create")
                continue
            
            exp_res = False if data_disk < RAID6_MIN_DISKS else True

            auto_create = True
            assert single_array_data_setup(pos.data_dict, "RAID6", data_disk,
                                spare_disk, array_mount, auto_create) == True

            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == exp_res

            if exp_res:
                array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
                assert pos.cli.info_array(array_name=array_name)[0] == True

                assert array_unmount_and_delete(pos) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_array_cap_with_volumes(array_mount):
    """
    The purpose of this test is to create RAID 6 array with different volumes and utilize its capacity.
    Verification: POS CLI - Array - Create, Mount, and List: Volume - Create, Mount, List
    """
    logger.info(
       f" ==================== Test : test_raid6_array_cap_with_volumes[{array_mount}] ================== "
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
        array_list = list(pos.cli.array_dict.keys())

        assert pos.cli.list_subsystem()[0] == True
        subsyste_list = pos.target_utils.ss_temp_list

        array_cap_volumes = [(1, 50), (1, 100), (1, 105), (50, 105), (256, 100), (257, 100)]

        for num_volumes, cap_utilize in array_cap_volumes:
            assert volume_create_and_mount_multiple(pos, num_volumes, cap_utilize,
                            array_list=array_list, subs_list=subsyste_list) == True

            assert volume_unmount_and_delete_multiple(pos, array_list) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("mount_order", [("WT", "WT"), ("WT", "WB"), ("WB", "WT"), ("WB", "WB"), 
                                         ("WB", "WT", "WB"), ("WT", "WB", "WT")])
@pytest.mark.parametrize("raid_type, num_disk", [("RAID6", RAID6_MIN_DISKS)])
def test_array_mount_unmount(raid_type, num_disk, mount_order):
    """
    The purpose of this test is to create RAID 6 array with different volumes selected randomaly.
    Verification: Array Mount and Unmount in Interportability
    """
    logger.info(
       f" ==================== Test : test_array_mount_unmount[{raid_type}-{num_disk}-{mount_order}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < num_disk:
            pytest.skip("Less number of data disk")

        auto_create = False
        assert single_array_data_setup(pos.data_dict, raid_type, RAID6_MIN_DISKS,
                                       0, mount_order[0], auto_create) == True
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        assert volume_create_and_mount_random(pos, array_list) == True

        for array_mount in mount_order[1:]:
            write_back = True if array_mount == "WB" else False
            array_name = array_list[0]
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
            assert pos.cli.mount_array(array_name=array_name, 
                                       write_back=write_back)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)