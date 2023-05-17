import pytest
import traceback

import logger
logger = logger.get_logger(__name__)

@pytest.fixture(scope="function")
def save_restore_fixture(system_fixture):
    pos = system_fixture
    assert pos.pos_conf.save_restore(enable=True, update_now=True) == True
    assert pos.target_utils.remove_restore_file() == True
    assert pos.target_utils.pos_bring_up() == True

    yield pos

    assert pos.pos_conf.save_restore(enable=False, update_now=True) == True
 

@pytest.mark.sanity
def test_save_restore_spor(save_restore_fixture):
    """
    The purpose of this test case is to Create and mount arrays, then
    create and mount volumes. Do SPOR and verify pos save restore feature
    """
    logger.info(
        " ================ Test : test_array_save_restore_spor ============="
    )
    try:
        pos = save_restore_fixture
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            array_data = pos.cli.array_dict[array_name]
            logger.info(f"Array - Name:{array_name}, Data:{array_data}")
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            #for vol_dict.keys()

        assert pos.target_utils.spor(save_restore=True, 
                                     restore_verify=True) == True

        assert pos.cli.array_list()[0] == True

        logger.info(" ===================== Test ENDs ===================== ")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        traceback.print_exc()


@pytest.mark.sanity
def test_save_restore_spor_clean_bringup(save_restore_fixture):
    """
    The purpose of this test case is to Create and mount arrays, then create 
    and mount volumes. Do SPOR, delete restore json and then bringup POS.
    """
    logger.info(
        " ================ Test : test_save_restore_spor_clean_bringup ============="
    )
    try:
        pos = save_restore_fixture
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            array_data = pos.cli.array_dict[array_name]
            logger.info(f"Array - Name:{array_name}, Data:{array_data}")
            assert pos.cli.volume_list(array_name=array_name)[0] == True

        assert pos.target_utils.remove_restore_file() == True
        assert pos.target_utils.spor(save_restore=False,
                                     restore_verify=False) == True

        assert pos.cli.array_list()[0] == True

        logger.info(" ===================== Test ENDs ===================== ")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        traceback.print_exc()

