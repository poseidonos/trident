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
@pytest.mark.parametrize(
    "normal,urgent,expected_result1,expected_result2",
    [
        (10.5, 3.5, True, True),
        (100000, 100000, False, False),
        (0, 0, False, False),
        (3, 10, False, False),
        ("ABC", "DEF", False, False),
        (-3, -3, False, False),
    ],
)
def test_set_gc_threshold_with_diff_values(
    normal, urgent, expected_result1, expected_result2
):
    logger.info(
        " ==================== Test : test_set_gc_threshold_with_diff_values ================== "
    )
    try:
        assert (
            pos.cli.wbt_set_gc_threshold(
                array_name=array_name, normal=normal, urgent=urgent
            )[0]
            == expected_result1
        )
        assert pos.cli.wbt_get_gc_status(array_name=array_name)[0] == expected_result2
        logger.info("As expected set gc failed because urgent is more than normal")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_get_gc_without_io():
    logger.info(
        " ==================== Test : test_get_gc_without_io ================== "
    )
    try:
        assert (
            pos.cli.volume_create(
                array_name=array_name, size="50gb", volumename="vol"
            )[0]
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn=ss_list[0]
            )
            == True
        )
        assert pos.cli.wbt_get_gc_status(array_name=array_name)[0] == True
        logger.info("As expected get gc failed because io is not run")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_gc_without_volume():
    logger.info(
        " ==================== Test : test_gc_without_volume ================== "
    )
    try:
        assert pos.cli.wbt_do_gc(array_name=array_name)[0] == False
        logger.info("As expected get gc failed because io is not run")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
