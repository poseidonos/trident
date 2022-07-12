import pytest
import traceback

from pos import POS
import logger

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")


    # TODO replace with relative path
    tgt_setup_file = "hetero_setup.json"
    conf_dir = "/root/nehal/trident/testcase/config_files/"

    data_path = f"{conf_dir}{tgt_setup_file}"
    tgt_conf_data = pos._json_reader(data_path, abs_path=True)[1]
    
    tgt_conf_data["enable"]="true"
    
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
        data_device_conf = {'20GiB': 1, 'any': 1}

        assert pos.target_utils.create_hetero_array(array_name, uram=uram_name,
                 data_device_config=data_device_conf, raid_type=raid_type) == True


    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
