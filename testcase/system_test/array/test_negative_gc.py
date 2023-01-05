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
    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["array"]["num_array"] = 0
    data_dict["volume"]["phase"] = "false"
    array_name = data_dict["array"]["pos_array"][0]["array_name"]
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
def test_set_gc_threshold_without_array():
    logger.info(
        " ==================== Test : test_set_gc_threshold_without_array ================== "
    )
    try:
        assert (
            pos.cli.wbt_set_gc_threshold(array_name="dummy", normal=10, urgent=3)[0]
            == False
        )
        logger.info("As expected set gc failed due to no array")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_get_gc_threshold_without_array():
    logger.info(
        " ==================== Test : test_get_gc_threshold_without_array ================== "
    )
    try:
        assert pos.cli.wbt_get_gc_threshold(array_name="dummy")[0] == False
        logger.info("As expected get gc failed due to no array")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_get_gc_status_without_array():
    logger.info(
        " ==================== Test : test_get_gc_status_without_array ================== "
    )
    try:
        assert pos.cli.wbt_get_gc_status(array_name="dummy")[0] == False
        logger.info("As expected get gc failed due to no array")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
