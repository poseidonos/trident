from pos import POS
import pytest
import time
import logger

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS()
    data_dict = pos.data_dict
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    #assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos

@pytest.mark.regression
def test_memory_check():
    try:
        start_time = time.time()
        run_time = 12*60
        end_time = start_time + (60 * run_time)
        logger.info("RunTime is {} minutes".format(run_time))
        while True:
            assert pos.target_utils.pos_bring_up() == True
            assert pos.cli.stop_system()[0] == True
            if time.time() > end_time:
                logger.info("Test script passed")
                break

    except Exception as e:
        pos.exit_handler()
        assert 0

def test_memory_noraid():
    try:
        assert pos.target_utils.pos_bring_up() == True
        assert pos.exit_handler(bool = True)
    except Exception as e:
        pos.exit_handler()
        assert 0
