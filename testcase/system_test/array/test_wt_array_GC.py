import pytest
from common_libs import *

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID10", 4), ("RAID5", 4)],
)
def test_wt_array_GC(array_fixture, raid_type, nr_data_drives):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(" ==================== Test : test_wt_array_GC ================== ")
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 1
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 0
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True

        run_io(pos)
        assert pos.cli.wbt_do_gc(array_name = array_name)[0] == False
        assert pos.cli.wbt_get_gc_status(array_name = array_name)[0] == False
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
