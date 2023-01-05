from pos import POS
import pytest
import time
import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
def test_memory_check():
    try:
        pos = POS()
        start_time = time.time()
        run_time = 12
        end_time = start_time + (60 * run_time)
        logger.info("RunTime is {} minutes".format(run_time))
        pos.data_dict["array"]["num_array"] = 1
        while True:
            assert pos.target_utils.pos_bring_up() == True
            assert pos.cli.system_stop()[0] == True
            if time.time() > end_time:
                logger.info("Test script passed")
                break

    except Exception as e:
        pos.exit_handler()
        assert 0


def test_memory_noraid():
    try:
        pos = POS()
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.pos_bring_up() == True
        assert pos.cli.system_stop()[0] == True
    except Exception as e:
        pos.exit_handler()
        assert 0
