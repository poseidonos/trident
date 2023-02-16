import pytest

import logger
logger = logger.get_logger(__name__)


@pytest.mark.regression
def test_set_gc_threshold_without_array(array_fixture):
    logger.info(
        " ==================== Test : test_set_gc_threshold_without_array ================== "
    )
    try:
        pos = array_fixture
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
def test_get_gc_threshold_without_array(array_fixture):
    logger.info(
        " ==================== Test : test_get_gc_threshold_without_array ================== "
    )
    try:
        pos = array_fixture
        assert pos.cli.wbt_get_gc_threshold(array_name="dummy")[0] == False
        logger.info("As expected get gc failed due to no array")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_get_gc_status_without_array(array_fixture):
    logger.info(
        " ==================== Test : test_get_gc_status_without_array ================== "
    )
    try:
        pos = array_fixture
        assert pos.cli.wbt_get_gc_status(array_name="dummy")[0] == False
        logger.info("As expected get gc failed due to no array")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
