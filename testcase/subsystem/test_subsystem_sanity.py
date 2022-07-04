import pytest
import logger
from pos import POS

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict, data_store
    pos = POS()
    data_store = {}
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "true"
    data_dict["subsystem"]["nr_subsystems"] = 512
    data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
    data_dict["volume"]["pos_volumes"][1]["num_vol"] = 256
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    yield pos


def teardown_function():

    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    assert pos.target_utils.get_subsystems_list() == True
    for ss in pos.target_utils.ss_temp_list:
        assert pos.cli.delete_subsystem(nqn_name=ss)[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.sanity
def test_sanitySubsystem():
    try:
        assert pos.target_utils.get_subsystems_list() == True

        assert pos.cli.list_array()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.list_volume(array)[0] == True
        assert pos.target_utils.get_subsystems_list() == True

    except Exception as e:
        logger.error(f"TC failed due to {e}")
        assert 0
