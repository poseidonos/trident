import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize("mount_order", [("WT", "WT"), ("WT", "WB"), ("WB", "WT"), ("WB", "WB"), 
                                         ("WB", "WT", "WB"), ("WT", "WB", "WT")])
@pytest.mark.parametrize("raid_type, num_disk", [("RAID6", RAID6_MIN_DISKS)])
def test_array_mount_unmount(array_fixture, raid_type, num_disk, mount_order):
    """
    The purpose of this test is to create RAID 6 array with different volumes selected randomaly.
    Verification: Array Mount and Unmount in Interportability
    """
    logger.info(
       f" ==================== Test : test_array_mount_unmount[{raid_type}-{num_disk}-{mount_order}] ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < num_disk:
            pytest.skip("Less number of data disk")

        auto_create = False
        assert single_array_data_setup(pos.data_dict, raid_type, RAID6_MIN_DISKS,
                                       0, mount_order[0], auto_create) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        assert volume_create_and_mount_random(pos, array_list) == True

        for array_mount in mount_order[1:]:
            write_back = True if array_mount == "WB" else False
            array_name = array_list[0]
            assert pos.cli.array_unmount(array_name=array_name)[0] == True
            assert pos.cli.array_mount(array_name=array_name, 
                                       write_back=write_back)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

