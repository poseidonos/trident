import pytest
import traceback

import logger
from common_libs import create_hetero_array

logger = logger.get_logger(__name__)

@pytest.mark.regression
def test_hetero_single_array_mount(array_fixture):
    """
    Create one RAID5 array using hetero devices and mount
    """
    logger.info(
        " ==================== Test : test_hetero_single_array_mount ================== "
    )
    try:
        pos = array_fixture
        raid_type = "RAID5"
        data_disk_req = {'mix': 2, 'any': 1}

        assert create_hetero_array(pos, raid_type, data_disk_req) == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
