import pytest

import logger
logger = logger.get_logger(__name__)


@pytest.mark.regression
def test_get_default_gc_threshold_value(array_fixture):
    logger.info(
        " ==================== Test : test_get_default_gc_threshold_value ================== "
    )
    try:
        pos = array_fixture
        data_dict = pos.data_dict
        data_dict["array"]["num_array"] = 1
        array_name = data_dict["array"]["pos_array"][0]["array_name"]

        pos.target_utils.bringup_array(data_dict=data_dict)
        status = pos.cli.wbt_get_gc_threshold(array_name=array_name)
        assert status[0] == True
        if (
            status[1]["output"]["Response"]["result"]["data"]["gc_threshold"]["normal"]
            == 20
        ) and (
            status[1]["output"]["Response"]["result"]["data"]["gc_threshold"]["urgent"]
            == 5
        ):
            logger.info("As expected default gc value is met")
        else:
            assert 0
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_gc_delete_array(array_fixture):
    logger.info(" ==================== Test : test_gc_delete_array ================== ")
    try:
        pos = array_fixture
        data_dict = pos.data_dict
        data_dict["array"]["num_array"] = 1
        array_name = data_dict["array"]["pos_array"][0]["array_name"]
        uram_name = data_dict["array"]["pos_array"][0]["uram"]

        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        assert pos.cli.array_create(array_name, write_buffer=uram_name,
                data=data_disk_list, spare=[], raid_type="RAID5")[0] == True

        assert pos.cli.array_delete(array_name=array_name)[0] == True
        assert pos.cli.wbt_do_gc(array_name=array_name)[0] == False
        logger.error("As expected gc fails without after deletion of array")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_gc_status(array_fixture):
    logger.info(" ==================== Test : test_gc_status ================== ")
    try:
        pos = array_fixture
        data_dict = pos.data_dict
        array_name = data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.cli.wbt_get_gc_status(array_name=array_name)[0] == False
        logger.error("As expected gc status will fail without do gc command")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
