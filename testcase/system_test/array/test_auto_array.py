import pytest

import logger
logger = logger.get_logger(__name__)


@pytest.mark.regression
def test_auto_array_with_all_numa(setup_cleanup_array_function):
    """
    Test auto create arrays of no-raid with different NUMA node
    """
    logger.info(
        " ==================== Test : test_auto_array_with_all_numa ================== "
    )
    try:
        pos = setup_cleanup_array_function
        numa_dev_list = [{"ssd": [], "nvram": []}, {"ssd": [], "nvram": []}]

        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        for dev in pos.cli.device_map:
            dev_type = pos.cli.device_map[dev]["type"].lower()
            dev_numa = int(pos.cli.device_map[dev]["numa"])
            numa_dev_list[dev_numa][dev_type].append(dev)

        # Autoarray create from using disk and uram from same num
        for numa_id, num_dev in enumerate(numa_dev_list):
            array_name = f"array{numa_id}"
            if num_dev["ssd"] and num_dev["nvram"]:
                assert (
                    pos.cli.autocreate_array(
                        num_dev["nvram"][0],
                        1,
                        "no-raid",
                        array_name=array_name,
                        num_spare=0,
                    )[0]
                    == True
                )

                assert pos.cli.info_array(array_name=array_name)[0] == True
                assert pos.cli.array_info[array_name]["state"] == "OFFLINE"

                assert pos.cli.mount_array(array_name=array_name)[0] == True
                assert pos.cli.info_array(array_name=array_name)[0] == True
                assert pos.cli.array_info[array_name]["state"] == "NORMAL"
            else:
                logger.info(f"Insufficient device {num_dev} to numa {numa_id}")

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


@pytest.mark.regression
def test_auto_array_with_insufficient_numa_dev(setup_cleanup_array_function):
    """
    Test auto create arrays of with insufficient NUMA node device
    """
    logger.info(
        " ==================== Test : test_auto_array_with_insufficient_numa_dev ================== "
    )
    try:
        pos = setup_cleanup_array_function
        numa_dev_list = [{"ssd": [], "nvram": []}, {"ssd": [], "nvram": []}]

        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        for dev in pos.cli.device_map:
            dev_type = pos.cli.device_map[dev]["type"].lower()
            dev_numa = int(pos.cli.device_map[dev]["numa"])
            numa_dev_list[dev_numa][dev_type].append(dev)

        # Autoarray create from using disk and uram from same num
        for numa_id, num_dev in enumerate(numa_dev_list):
            array_name = f"array{numa_id}"
            if len(num_dev["ssd"]) >= 3 and num_dev["nvram"]:
                assert (
                    pos.cli.autocreate_array(
                        num_dev["nvram"][0],
                        len(num_dev["ssd"]) + 1,
                        "RAID5",
                        array_name=array_name,
                        num_spare=0,
                    )[0]
                    == False
                )
            else:
                logger.info(f"Insufficient device {num_dev} to numa {numa_id}")

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
