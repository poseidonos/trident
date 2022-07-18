import pytest
import traceback

from pos import POS
import logger

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, min_hetero_dev
    pos = POS("pos_config.json")

    # TODO replace with relative path
    tgt_setup_file = "hetero_setup.json"
    conf_dir = "/root/nehal/trident/testcase/config_files/"

    data_path = f"{conf_dir}{tgt_setup_file}"
    tgt_conf_data = pos._json_reader(data_path, abs_path=True)[1]
    
    if tgt_conf_data["enable"] == "false":
        logger.warning("The enable flag is not true in hetero_setup.json file.")

    min_hetero_dev = 2
    if (min_hetero_dev < tgt_conf_data["num_test_device"]):
        logger.warning("The setup required minimum {} Hetero devices. "
                       "Only {} Hetero devices is added in config file".format(
                        min_hetero_dev, tgt_conf_data["num_test_device"]))
        pytest.skip("Required condition not met. Refer to logs for more details")
    
    pos.target_utils.hetero_setup.prepare(tgt_conf_data)

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
def test_hetero_setup_play():
    logger.info(
        " ==================== test_hetero_setup_play ================== "
    )


@pytest.mark.regression
def test_hetero_array_sample():
    """
    Test auto create arrays of no-raid with different NUMA node
    """
    logger.info(
        " ==================== Test : test_hetero_array_sample ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        array_name = "array1"
        raid_type = "RAID0"
        uram_name = data_dict["device"]["uram"][0]["uram_name"]

        data_device_conf = {'20GiB': 0, 'mix': 1, 'any':4}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                    spare=spare_drives, raid_type=raid_type,
                                    array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )
