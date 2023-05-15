import pytest
from common_libs import *
import logger
logger = logger.get_logger(__name__)

def test_cmd_prgrs_sanity(array_fixture):
    '''
    the purpose of the test is to verify 
    command progress of mouinting the array and unmounting the array
    '''
    try:
        logger.info(
            f" ============== Test : start of test_cmd_prgrs_sanity  ============="
        )
        pos = array_fixture
        #creating array
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        single_array_data_setup(pos.data_dict, "RAID5", 4, 0, "NO", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        assert pos.cli.array_info(array_name=array_name)[0] == True
        #verifying array mount progress in report.log
        mount_progress = pos.target_utils.report_log_array("array_mount")
        logger.info(mount_progress)
        if array_name in mount_progress:
               logger.info(
            f" ============== array mount command progress verified successfully  ============="
        )
        #verifying volume mount progress in report.log
        assert pos.cli.volume_create(array_name=array_name,volumename="vol1",size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name,vol_name="vol1")[0] == True
        cmd_mount_out = pos.target_utils.report_log_volume("volume_mount")
        logger.info(cmd_mount_out)
        if "vol1" in cmd_mount_out:
               logger.info(
            f" ============== volume mount command progress verified successfully  ============="
        )
        #verifying volume unmount progress in report.log
        assert pos.cli.volume_unmount(array_name=array_name,volumename="vol1")[0] == True
        cmd_unmount_out = pos.target_utils.report_log_volume("volume_unmount")
        logger.info(cmd_unmount_out)
        if "vol1" in cmd_unmount_out:
               logger.info(
            f" ============== volume unmount command progress verified successfully  ============="
        )
        #verifying array unmount progress in report.log
        assert pos.cli.array_unmount(array_name=array_name)[0] == True
        unmount_progress = pos.target_utils.report_log_array("array_unmount")
        logger.info(unmount_progress)
        if array_name in unmount_progress:
               logger.info(
            f" ============== array unmount command progress verified successfully  ============="
        )
        logger.info(
            f" ============== Test : end of test_cmd_prgrs_sanity  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)