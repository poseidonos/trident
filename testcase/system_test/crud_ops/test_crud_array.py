import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression
def test_crud_array_ops_all_raids(array_fixture):
    """
    The purpose of this test is to do array crud operation with following matrix.

    RAID Types - (no-raid, raid0, raid5, raid6, raid10)
    Operations - 
        C: create / autocreate
        R: list
        U: addspare / mount / rebuild / replace / rmspare / unmount
        D: delete

    Verification: POS CLI - Array CRUD Operation.
    """
    logger.info(
        f" ==================== Test : test_crud_array_ops_all_raids ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        
        for arr1_raid in ARRAY_ALL_RAID_LIST:
            arr2_raid = random.choice(ARRAY_ALL_RAID_LIST)
            arr1_disk = RAID_MIN_DISK_REQ_DICT[arr1_raid]
            arr2_disk = RAID_MIN_DISK_REQ_DICT[arr2_raid]

            if (arr1_disk + arr2_disk + 2) > len(system_disks):
                logger.warning("Array creation requied more disk")
                continue

            assert multi_array_data_setup(pos.data_dict, 2, (arr1_raid, arr2_raid),
                                          (arr1_disk, arr2_disk), (0, 0), 
                                          ("WT", "WT"), (False, True)) == True

            # Create, Read and Update Ops
            assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

            # Read and Update Ops
            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())

            assert pos.cli.device_list()[0] == True
            system_disks = pos.cli.system_disks
            for array_name in array_list:
                assert pos.cli.array_info(array_name=array_name)[0] == True
                array_raid = pos.cli.array_data[array_name]["data_raid"]
                data_disk = pos.cli.array_data[array_name]["data_list"]

                # spare disk is not supported, continue
                if array_raid == "RAID0" or array_raid == None:
                    continue

                spare_disk = system_disks.pop(0)
                assert pos.cli.array_addspare(device_name=spare_disk,
                                              array_name=array_name)[0] == True
                
                assert pos.cli.array_rmspare(device_name=spare_disk,
                                             array_name=array_name)[0] == True
                
                assert pos.cli.array_addspare(device_name=spare_disk,
                                              array_name=array_name)[0] == True

                assert pos.cli.array_replace_disk(device_name=data_disk[0],
                                                array_name=array_name)[0] == True

            # Update and Delete Operation
            assert array_unmount_and_delete(pos) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_crud_array_negative_ops(array_fixture):
    """
    The purpose of this test is to do negative array crud operation.

    RAID Types - (raid5, raid6, raid10)
    Operations - 
        C: create / autocreate
        R: list
        U: addspare / mount / rebuild / replace / rmspare / unmount
        D: delete

    Verification: POS CLI - Array CRUD Operation.
    """
    logger.info(
        f" ==================== Test : test_crud_array_ops_all_raids ================== "
    )
    pos = array_fixture
    try:
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        # Create Array with invalid RAID
        single_array_data_setup(pos.dict, "RAID_ERR", 4, 0, "NO", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == False
        logger.info("Expected failure for create Array with invalid RAID")

        # Create Array with less than minimim required disk
        single_array_data_setup(pos.dict, "RAID5", 2, 0, "NO", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == False
        logger.info("Expected failure for create Array with less Disk")

        # Info Array which is not created
        assert pos.cli.array_info(array_name=array_name)[0] == False
        logger.info("Expected failure for info Array which is not created")

        # Mount Array which is not created
        assert pos.cli.array_mount(array_name=array_name)[0] == False
        logger.info("Expected failure for list Array which is not created")

        # Delete Array which is not created
        assert pos.cli.array_delete(array_name=array_name)[0] == False
        logger.info("Expected failure for delete Array which is not created")

        # Create a valid Array with RAID 5 (+ve)
        single_array_data_setup(pos.dict, "RAID5", 4, 0, "WT", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        # Unmount the unmounted Array
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == False
        logger.info("Expected failure for re-create Array")

        # Mount the array in WT (+ve)
        assert pos.cli.array_mount(array_name=array_name)[0] == True

        # Mount same Array Again
        assert pos.cli.array_mount(array_name=array_name)[0] == False
        logger.info("Expected failure for re-mount same Array")

        assert pos.cli.array_info(array_name=array_name)[0] == True
        data_disks = pos.cli.array_data[array_name]["data_list"]

        # Add existing data disk as spare disk
        assert pos.cli.array_addspare(device_name=data_disks[0],
                                      array_name=array_name)[0] == False
        logger.info("Expected failure for add data disk as spare disk")

        # Remove data disk using rmspare command
        assert pos.cli.array_rmspare(device_name=data_disks[0],
                                     array_name=array_name)[0] == False
        logger.info("Expected failure for remove data disk as spare disk")

        # Replace data disk without spare disk
        assert pos.cli.array_replace_disk(device_name=data_disks[0],
                                        array_name=array_name)[0] == False
        logger.info("Expected failure for array replace disk")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)



