import pytest
import traceback
import time

import logger
logger = logger.get_logger(__name__)


@pytest.mark.sanity
def test_pos_start_after_reboot(system_fixture):
    """
    The purpose of this test case is to verify POS is running after system
    reboot.
    """
    logger.info(
        " ================ Test : test_pos_start_after_reboot ============="
    )
    try:
        pos = system_fixture
        if pos.pos_as_service == False: 
            pytest.skip("POS should run as a service for telemetry to work")

        assert pos.target_utils.reboot_and_reconnect() == True

        # Wait for 2 minutes 
        logger.info("Wait for 2 minutes after system start")
        time.sleep(120)

        # Return False if pos is running
        assert pos.target_utils.helper.check_pos_exit() == False

        logger.info(" ===================== Test ENDs ===================== ")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        traceback.print_exc()