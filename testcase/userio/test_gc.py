import pytest

# from lib.pos import POS
import logger
import random
from common_libs import *

logger = logger.get_logger(__name__)



@pytest.mark.sanity
def test_do_gc_emptyarray(array_fixture):
    try:
        """GC is expected to fail on 100% Free array"""
        pos = array_fixture
        assert pos.cli.wbt_do_gc()[0] == False
    except Exception as e:
        logger.error(e)
        pos.exit_handler()


@pytest.mark.sanity
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("RAID0", 2), ("RAID10", 4), ("RAID10", 2), ("no-raid", 1), ("RAID10", 8)],)
def test_gcMaxvol(array_fixture, raid_type, nr_data_drives):
    """Trigger garbage collection with longevity of I/O"""
    try:
        pos = array_fixture
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][0]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][1]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 0
        pos.data_dict["array"]["pos_array"][1]["spare_device"] = 0
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = 256

        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
        pos.cli.wbt_do_gc()
        pos.cli.wbt_get_gc_status()
        

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()
