import pytest

import time
from common_libs import *

import logger
logger = logger.get_logger(__name__)

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
        f" ==================== Test : test_crud_array_negative_ops ================== "
    )
    pos = array_fixture
    try:
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        # Create Array with invalid RAID
        single_array_data_setup(pos.data_dict, "RAID_ERR", 4, 0, "NO", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == False
        logger.info("Expected failure for create Array with invalid RAID")

        # Create Array with less than minimim required disk
        single_array_data_setup(pos.data_dict, "RAID5", 2, 0, "NO", False)
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
        single_array_data_setup(pos.data_dict, "RAID5", 4, 0, "WT", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

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



