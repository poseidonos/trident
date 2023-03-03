import pytest

import logger

logger = logger.get_logger(__name__)


def array_setup(pos):
    global data_dict, array_name
    data_dict = pos.data_dict
    data_dict["array"]["num_array"] = 1
    array_name = data_dict["array"]["pos_array"][0]["array_name"]
    assert pos.target_utils.bringup_array(data_dict=data_dict) == True

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
def test_set_gc_threshold_with_diff_values(array_fixture,
    normal, urgent, expected_result1, expected_result2
):
    logger.info(
        " ==================== Test : test_set_gc_threshold_with_diff_values ================== "
    )
    try:
        pos = array_fixture
        array_setup(pos)
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


def test_get_gc_without_io(array_fixture):
    logger.info(
        " ==================== Test : test_get_gc_without_io ================== "
    )
    try:
        pos = array_fixture
        array_setup(pos)
        assert pos.cli.volume_create(array_name=array_name,
                                     size="50gb", volumename="vol")[0] == True

        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        subsys_list = pos.target_utils.ss_temp_list
        ss_list = [ss for ss in subsys_list if array_name in ss]
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                            volume_list=pos.cli.vols, nqn=ss_list[0]) == True

        assert pos.cli.wbt_get_gc_status(array_name=array_name)[0] == True
        logger.info("As expected get gc failed because io is not run")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_gc_without_volume(array_fixture):
    logger.info(
        " ==================== Test : test_gc_without_volume ================== "
    )
    try:
        pos = array_fixture
        array_setup(pos)
        assert pos.cli.wbt_do_gc(array_name=array_name)[0] == False
        logger.info("As expected get gc failed because io is not run")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
