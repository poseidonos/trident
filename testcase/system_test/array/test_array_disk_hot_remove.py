import pytest

from pos import POS

import logger
logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict['array']['phase'] = "false"
    data_dict['volume']['phase'] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos

def setup_function():
    data_dict = pos.data_dict
    if pos.target_utils.helper.check_pos_exit() == True:
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

    data_dict['system']['phase'] = "false"
    data_dict['device']['phase'] = "false"
    data_dict['subsystem']['phase'] = "false"
    data_dict['array']['phase'] = "true"

def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.cli.list_array()[0] == True
    for array_name in pos.cli.array_dict.keys():
        assert pos.cli.info_array(array_name=array_name)[0] == True
        if pos.cli.array_dict[array_name].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.delete_array(array_name=array_name)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
def test_array_after_disk_remove():
    logger.info(
        " ==================== Test : test_array_after_disk_remove ================== "
    )
    try:
        assert pos.cli.list_device()
        hot_remove_disks = pos.cli.system_disks.pop(0)

        assert pos.target_utils.device_hot_remove([hot_remove_disks])

        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)