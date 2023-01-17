import pytest
import logger

logger = logger.get_logger(__name__)

@pytest.mark.regression
def test_array_after_disk_remove(array_fixture):
    logger.info(
        " ==================== Test : test_array_after_disk_remove ================== "
    )
    try:
        pos = array_fixture
        assert pos.cli.device_list()
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
