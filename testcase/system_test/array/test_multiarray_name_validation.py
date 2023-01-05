import pytest
import traceback

from pos import POS
import random
import time
import pprint

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "new_name,expected_result", [("b" * 63, True), ("array1", False), ("a" * 64, False)]
)
def test_multi_array_name(setup_cleanup_array_function, new_name, expected_result):
    logger.info(
        " ==================== Test : test_multi_array_name ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        spare_disk_list = []
        assert (
            pos.cli.array_create(
                write_buffer="uram1",
                data=data_disk_list,
                spare=spare_disk_list,
                raid_type="RAID5",
                array_name=new_name,
            )[0]
            == expected_result
        )
        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True
                assert pos.cli.array_delete(array_name=array)[0] == True
        logger.info("As expected array creation failed with same array name ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0
