import pytest
import traceback

from pos import POS
import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
def test_auto_array_with_all_numa():
    """
    Test auto create arrays of no-raid with different NUMA node
    """
    logger.info(
        " ==================== Test : test_auto_array_with_all_numa ================== "
    )
    try:
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
def test_auto_array_with_insufficient_numa_dev():
    """
    Test auto create arrays of with insufficient NUMA node device
    """
    logger.info(
        " ==================== Test : test_auto_array_with_insufficient_numa_dev ================== "
    )
    try:
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
