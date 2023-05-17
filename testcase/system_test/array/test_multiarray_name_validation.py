import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "new_name,expected_result", [("b" * 63, True), ("array1", False), ("a" * 64, False)]
)
def test_multi_array_name(array_fixture, new_name, expected_result):
    logger.info(
        " ==================== Test : test_multi_array_name ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]

        assert pos.cli.array_create(array_name=new_name,
                write_buffer="uram1", data=data_disk_list,
                spare=[], raid_type="RAID5")[0] == expected_result

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.array_unmount(array_name=array)[0] == True
                assert pos.cli.array_delete(array_name=array)[0] == True
        logger.info("As expected array creation failed with same array name ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
