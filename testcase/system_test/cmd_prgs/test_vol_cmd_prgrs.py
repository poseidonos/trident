import pytest
from common_libs import *
import logger
logger = logger.get_logger(__name__)

def test_vol_cmd_prgrs(array_fixture):
    '''
    the purpose of the test is to verify 
    command progress of mouinting the volume and unmounting the volume
    '''
    try:
        logger.info(
            f" ============== Test : start of test_vol_cmd_prgrs  ============="
        )
        pos = array_fixture
        #creating array
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        single_array_data_setup(pos.data_dict, "RAID5", 4, 0, "NO", False)
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        assert pos.cli.array_info(array_name=array_name)[0] == True
        #verifying volume mount progress in report.log
        assert pos.cli.volume_create(array_name=array_name,volumename="vol1",size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name,vol_name="vol1")[0] == True
        cmd_mount_out = pos.target_utils.report_log("volume_mount")
        logger.info(cmd_mount_out)
        if "vol1" in cmd_mount_out:
               logger.info(
            f" ============== volume mount command progress verified successfully  ============="
        )
        #verifying volume unmount progress in report.log
        assert pos.cli.volume_unmount(array_name=array_name,volumename="vol1")[0] == True
        cmd_unmount_out = pos.target_utils.report_log("volume_unmount")
        logger.info(cmd_unmount_out)
        if "vol1" in cmd_unmount_out:
               logger.info(
            f" ============== volume unmount command progress verified successfully  ============="
        )
        logger.info(
            f" ============== Test : end of test_vol_cmd_prgrs  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)