import pytest
import traceback

from pos import POS
import logger
import random
import time
import pprint

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, array_name
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["array"]["num_array"] = 1
    data_dict["volume"]["phase"] = "false"
    array_name = data_dict["array"]["pos_array"][0]["array_name"]
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.cli.array_list()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.array_unmount(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
def test_get_default_gc_threshold_value():
    logger.info(
        " ==================== Test : test_get_default_gc_threshold_value ================== "
    )
    try:
        status = pos.cli.wbt_get_gc_threshold(array_name=array_name)
        assert status[0] == True
        if (
            status[1]["output"]["Response"]["result"]["data"]["gc_threshold"]["normal"]
            == 20
        ) and (
            status[1]["output"]["Response"]["result"]["data"]["gc_threshold"]["urgent"]
            == 5
        ):
            logger.info("As expected default gc value is met")
        else:
            assert 0
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_gc_delete_array():
    logger.info(" ==================== Test : test_gc_delete_array ================== ")
    try:
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        assert (
            pos.cli.array_create(
                write_buffer="uram1",
                data=data_disk_list,
                spare=[],
                raid_type="RAID5",
                array_name="array_gc",
            )[0]
            == True
        )
        assert pos.cli.array_delete(array_name="array_gc")[0] == True
        assert pos.cli.wbt_do_gc()[0] == False
        logger.error("As expected gc fails without after deletion of array")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_gc_status():
    logger.info(" ==================== Test : test_gc_status ================== ")
    try:
        assert pos.cli.wbt_get_gc_status()[0] == False
        logger.error("As expected gc status will fail without do gc command")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
