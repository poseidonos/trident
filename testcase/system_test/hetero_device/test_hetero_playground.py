import pytest
import traceback

from pos import POS
import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, tgt_conf_data
    pos = POS("pos_config.json")

    # TODO replace with relative path
    tgt_setup_file = "hetero_setup.json"
    conf_dir = "../../config_files/"

    data_path = f"{conf_dir}{tgt_setup_file}"
    tgt_conf_data = pos._json_reader(data_path, abs_path=True)[1]

    logger.info(f"Hetero Setup Json : {tgt_conf_data}")

    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    #pos.exit_handler(expected=True)

@pytest.mark.parametrize("action", ["setup", "reset", "reset_delete", "setup_reset"])
def test_hetero_setup_play(action):
    logger.info(" ==================== test_hetero_setup_play ================== ")
    if tgt_conf_data["enable"] == "false":
        logger.warning("The enable flag is not true in hetero_setup.json file.")

    tgt_conf_data["enable"] = "true"
    tgt_setup = pos.target_utils.hetero_setup

    if action == "setup":
        assert tgt_setup.prepare(tgt_conf_data)
    elif action == "reset":
        assert tgt_setup.reset(tgt_conf_data)
    elif action == "reset_delete":
        assert tgt_setup.reset(tgt_conf_data, remove_recovery_file=True)
    elif action == "setup_reset":
        assert tgt_setup.prepare(tgt_conf_data)
        assert tgt_setup.reset(tgt_conf_data)


@pytest.mark.regression
def test_hetero_array_sample():
    """
    Test auto create arrays of no-raid with different NUMA node
    """
    logger.info(
        " ==================== Test : test_hetero_array_sample ================== "
    )
    try:
        data_dict = pos.data_dict
        data_dict["array"]["phase"] = "false"
        data_dict["volume"]["phase"] = "false"
        assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
        assert pos.cli.devel_resetmbr()[0] == True
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True

        array_name = data_dict["array"]["pos_array"][0]["array_name"]
        raid_type = data_dict["array"]["pos_array"][0]["raid_type"]
        uram_name = data_dict["device"]["uram"][0]["uram_name"]

        data_device_conf = {"20GiB": 0, "mix": 1, "any": 4}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert (
            pos.cli.array_create(
                write_buffer=uram_name,
                data=data_drives,
                spare=spare_drives,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=True)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
