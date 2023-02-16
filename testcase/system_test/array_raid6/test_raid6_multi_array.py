import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression
@pytest.mark.parametrize("array_mount", [("WT", "WT"), ("WB", "WB"), ("WT", "WB"), ("WB", "WT")])
def test_mount_raid6_array_with_all_raids(array_fixture, array_mount):
    """
    The purpose of this test is to create two arrays. One of them should be RAID 6 always.
    Verification: POS CLI - Create Array Mount Array and List Array command.
                  Multi Array Operability. 
    """
    logger.info(
        f" ==================== Test : test_mount_raid6_array_with_all_raids[{array_mount}] ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        
        for raid_type in ARRAY_ALL_RAID_LIST:
            num_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
            arrays_num_disks = (RAID6_MIN_DISKS, num_disk)

            if sum(arrays_num_disks) > len(system_disks):
                logger.warning("Array creation requied more disk")
                continue

            assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", raid_type), 
                        arrays_num_disks, (0, 0), array_mount,  (False, False)) == True

            assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

            assert array_unmount_and_delete(pos) == True

        
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("raid_type", ARRAY_ALL_RAID_LIST)
def test_random_volumes_on_raid6_arrays(array_fixture, raid_type):
    """
    The purpose of this test is to create two array and either should be RAID 6. 
    Create and mount different volumes and utilize its capacity selectly randomally.
    Verification: POS CLI - Array - Create, Mount, and List: Volume - Create, Mount, List
    """
    logger.info(
        f" ==================== Test : test_random_volumes_on_raid6_array[{raid_type}] ================== "
    )
    pos = array_fixture
    try:
        num_disks = RAID_MIN_DISK_REQ_DICT[raid_type]
        arrays_num_disks = (RAID6_MIN_DISKS, num_disks)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", raid_type),
                    arrays_num_disks, (0, 0), ("WT", "WB"), (False, False)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert volume_create_and_mount_random(pos) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("num_vols", [2, 256])
def test_raid6_arrays_file_block_io(array_fixture, num_vols):
    """
    The purpose of this test is to create two arrays and atleast 1 should be RAID 6. 
    Create and mount different volumes and utilize its capacity selectly randomally.
    Run File IO, Block IO and Mix of File and Block IO.
    Verification: POS CLI, End to End Data Flow
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_file_block_io[{num_vols}] ================== "
    )
    pos = array_fixture
    try:
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", "RAID6"), 
                                      arrays_num_disks, (0, 0), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, num_vols,
                                                subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        for fio_type in ["Block", "Mix", "File"]:
            assert run_fio_all_volumes(pos, fio_type=fio_type) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_create_arrays_vol_delete_arrays_vol(array_fixture):
    logger.info(
        f" ==================== Test : test_create_arrays_vol_delete_arrays_vol ================== "
    )
    try:
        pos = array_fixture
        assert multi_array_data_setup(data_dict=pos.data_dict, num_array=2,
                                      raid_types=("RAID6","RAID6"),
                                      num_data_disks=(4,4),
                                      num_spare_disk=(1,1),
                                      auto_create=(True, True),
                                      array_mount=("WT", "WT")) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        num_vols=[1,128,256]
        for num in num_vols:
            assert volume_create_and_mount_multiple(pos=pos, num_volumes=num, array_list=pos.cli.array_dict.keys(),
                                                    subs_list=pos.target_utils.ss_temp_list) == True
            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())

            assert volume_unmount_and_delete_multiple(pos, array_list) == True

        assert array_unmount_and_delete(pos) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
