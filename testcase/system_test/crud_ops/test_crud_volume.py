import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)

def common_setup(pos):
    assert pos.cli.device_list()[0] == True
    system_disks = pos.cli.system_disks
    
    arr1_raid, arr2_raid = "RAID5", "RAID10"

    arr1_disk = RAID_MIN_DISK_REQ_DICT[arr1_raid]
    arr2_disk = RAID_MIN_DISK_REQ_DICT[arr2_raid]

    if (arr1_disk + arr2_disk + 2) > len(system_disks):
        pytest.skip("Array creation requied more disk")

    assert multi_array_data_setup(pos.data_dict, 2, (arr1_raid, arr2_raid),
                                    (arr1_disk, arr2_disk), (0, 0), 
                                    ("WT", "WT"), (False, True)) == True
    assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

@pytest.mark.regression
def test_crud_volume_ops(array_fixture):
    """
    The purpose of this test is to do volume crud operation on RAID5 and RAID10
    arrays for following matrix.

    Array RAID Types - (raid5, raid10)
    Operations - 
        C: create
        R: list
        U: mount / mount-with-subsystem / rename / set-property / unmount
        D: delete

    Verification: POS CLI - Volume CRUD Operation.
    """
    logger.info(
        f" ==================== Test : test_crud_volume_ops ================== "
    )
    pos = array_fixture
    try:
        common_setup(pos)
        array_list = list(pos.cli.array_dict.keys())

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        nr_vol_list = [1, 16, 256]
        for num_vols in nr_vol_list:
            logger.info(f"Create, Mount, List, Unmount, Delete {num_vols} Vols")
            # Create, Read and Update Ops
            assert volume_create_and_mount_multiple(pos, num_vols, 
                        array_list=array_list, subs_list=subs_list) == True
            
            # Update and Delete Operation
            assert volume_unmount_and_delete_multiple(pos, array_list) == True

        # Create 2 volumes from each array
        assert volume_create_and_mount_multiple(pos, 2, array_list=array_list,
                                mount_vols=False, subs_list=subs_list) == True
        
        for array_name in array_list:
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name in pos.cli.vol_dict.keys():
                assert pos.cli.volume_rename("new" + vol_name, vol_name,
                                        array_name=array_name)[0] == True
                #assert pos.cli.volume_mount_with_subsystem()

        # Update and Delete Operation
        assert volume_unmount_and_delete_multiple(pos, array_list) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_crud_volume_negative_ops(array_fixture):
    """
    The purpose of this test is to do negative array crud operation.

    RAID Types - (raid5, raid10)
    Operations - 
        C: create
        R: list
        U: mount / mount-with-subsystem / rename / set-property / unmount
        D: delete

    Verification: POS CLI - Array CRUD Operation.
    """
    logger.info(
        f" ==================== Test : test_crud_volume_negative_ops ================== "
    )
    pos = array_fixture
    try:
        common_setup(pos)
        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        subs_list = pos.target_utils.ss_temp_list

        array_cap = []
        for array_name in array_list:
            assert pos.cli.array_info(array_name=array_name)[0] == True
            size = int(pos.cli.array_data[array_name]["size"]) // (1024 * 1024)
            array_cap.append(size)

        vol_size_mb = f"{array_cap[0]}mb"
        vol_size_err =f"{array_cap[0]}gb"
    
        # Create volume with invalid array
        assert pos.cli.volume_create("Vol_Err", vol_size_mb,
                                     "Array_Err")[0] == False
        logger.info("Expected failure for volume create with invalid array")

        # Create volume with size more than array capacity
        assert pos.cli.volume_create("Vol_Err", vol_size_err,
                                     array_list[0])[0] == False
        logger.info("Expected failure for volume create with invalid size")

        # Mount uncreated Volume with an array
        assert pos.cli.volume_mount(volumename="Vol_Err",
                                    array_name=array_list[0],
                                    nqn=subs_list[0])[0] == False
        logger.info("Expected failure for volume mount with invalid volume")
        
        # Mount uncreated Volume with an array
        assert pos.cli.volume_delete(volumename="Vol_Err",
                                    array_name=array_list[0])[0] == False
        logger.info("Expected failure for volume delete with invalid volume")
        
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)



