import pytest
from common_libs import *
import logger
logger = logger.get_logger(__name__)

def test_array_cmd_prgrs(array_fixture):
    '''
    the purpose of the test is to verify 
    command progress of mouinting the array and unmounting the array
    '''
    try:
        logger.info(
            f" ============== Test : start of test_array_cmd_prgrs  ============="
        )
        pos = array_fixture
        #creating array
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        single_array_data_setup(pos.data_dict, "RAID5", 4, 0, "NO", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        assert pos.cli.array_info(array_name=array_name)[0] == True
        #verifying array mount progress in report.log
        mount_progress = pos.target_utils.report_log("array_mount")
        logger.info(mount_progress)
        if array_name in mount_progress:
               logger.info(
            f" ============== array mount command progress verified successfully  ============="
        )
        #verifying array unmount progress in report.log
        assert pos.cli.array_unmount(array_name=array_name)[0] == True
        unmount_progress = pos.target_utils.report_log("array_unmount")
        logger.info(unmount_progress)
        if array_name in unmount_progress:
               logger.info(
            f" ============== array unmount command progress verified successfully  ============="
        )
        logger.info(
            f" ============== Test : end of test_array_cmd_prgrs  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)