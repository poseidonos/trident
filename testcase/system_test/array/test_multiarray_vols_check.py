import pytest
import traceback

from pos import POS
import random
import time
import pprint

from common_multiarray import *
import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
def test_multi_array_create_vols(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_array_create_vols ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        for array_name in array_list:
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_cap_before = pos.cli.array_data[array_name]["size"]
            logger.info("Array capcatity after {}".format(array_cap_before))

        assert (
            pos.target_utils.create_volume_multiple(
                array_name=array_name, num_vol=5, vol_name="vol"
            )
            == True
        )

        for array_name in array_list:
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_cap_after = pos.cli.array_data[array_name]["size"]
            logger.info("Array capcatity after {}".format(array_cap_after))

        logger.info("As expected array size vary before and after volume creation ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_multi_array_delete_vols(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_array_del_vols ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        for array_name in array_list:
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array_name, num_vol=5, vol_name="vol"
                )
                == True
            )
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_cap_creation = pos.cli.array_data[array_name]["size"]
            logger.info("Array capcatity after {}".format(array_cap_creation))
            assert pos.target_utils.delete_all_volumes(arrayname=array_name) == True
            array_cap_creation = pos.cli.array_data[array_name]["size"]
            logger.info("Array capcatity after {}".format(array_cap_creation))
            logger.info(
                " ============================= Test ENDs ======================================"
            )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_multi_array_invalid_vols(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_array_invalid_vols ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        for array_name in array_list:
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            assert (
                pos.cli.volume_create(
                    array_name=array_name, volumename="###", size="100gb"
                )[0]
                == False
            )
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        logger.info("As expected array size vary before and after volume creation ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0
