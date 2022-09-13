import time
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
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True
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
@pytest.mark.parametrize("array_mount", [("WT", "WT"), ("WB", "WB"), ("WT", "WB"), ("WB", "WT")])
def test_mount_raid6_array_with_all_raids(array_mount):
    """
    The purpose of this test is to create two arrays. One of them should be RAID 6 always.
    Verification: POS CLI - Create Array Mount Array and List Array command.
                  Multi Array Operability. 
    """
    logger.info(
        f" ==================== Test : test_mount_raid6_array_with_all_raids[{array_mount}] ================== "
    )
    try:
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        

        for raid_type, num_disk in ARRAY_ALL_RAID_LIST:
            arrays_raid_type = ("RAID6", raid_type)
            arrays_num_disks = (RAID6_MIN_DISKS, num_disk)
            arrays_auto_create = (False, False)

            if sum(arrays_num_disks) > len(system_disks):
                logger.warning("Array creation requied more disk")
                continue

            assert multi_array_data_setup(pos.data_dict, 2, arrays_raid_type, arrays_num_disks,
                                        (0, 0), array_mount,  arrays_auto_create) == True

            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

            assert array_unmount_and_delete() == True

        
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("raid_type, num_disks", ARRAY_ALL_RAID_LIST)
def test_random_volumes_on_raid6_arrays(raid_type, num_disks):
    """
    The purpose of this test is to create two array and either should be RAID 6. 
    Create and mount different volumes and utilize its capacity selectly randomally.
    Verification: POS CLI - Array - Create, Mount, and List: Volume - Create, Mount, List
    """
    logger.info(
        f" ==================== Test : test_random_volumes_on_raid6_array[{raid_type}-{num_disks}-{array_mount}] ================== "
    )
    try:
        arrays_raid_type = ("RAID6", raid_type)
        arrays_num_disks = (RAID6_MIN_DISKS, num_disks)
        arrays_auto_create = (False, True)
        array_mount = ("WT", "WB")

        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, arrays_raid_type, arrays_num_disks,
                                      (0, 0), array_mount, arrays_auto_create) == True
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert volume_create_and_mount_random(pos) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("fio_type", ["File", "Block", "Mix"])
@pytest.mark.parametrize("num_vols", [2, 256])
def test_raid6_arrays_fio(raid_type, num_disks, num_vols, fio_type):
    """
    The purpose of this test is to create two array and either should be RAID 6. 
    Create and mount different volumes and utilize its capacity selectly randomally.
    Verification: POS CLI - Array - Create, Mount, and List: Volume - Create, Mount, List
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_fio[{raid_type}-{num_disks}-{array_mount}-{fio_type}] ================== "
    )
    try:
        arrays_raid_type = ("RAID6", "RAID6")
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        arrays_auto_create = (False, True)
        array_mount = ("WT", "WB")

        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, arrays_raid_type, 
                                      arrays_num_disks, (0, 0), array_mount,
                                      arrays_auto_create) == True
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert pos.cli.list_subsystem()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, num_vols,
                                                subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert run_fio_all_volumes(fio_type=fio_type) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)