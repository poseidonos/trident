import pytest
import traceback

from pos import POS
import logger

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, min_hetero_dev
    pos = POS("pos_config.json")

    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    assert pos.cli.devel_resetmbr()[0] == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    for array in pos.cli.array_dict.keys():
        assert pos.cli.array_info(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
def test_hetero_single_array_mount():
    """
    Create one RAID5 array using hetero devices and mount
    """
    logger.info(
        " ==================== Test : test_hetero_single_array_mount ================== "
    )
    try:
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True

        if len(pos.cli.system_disks) < 3:
            pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                        f"Required minimum 3 disk to create RAID5 array")

        array_name = "array1"
        uram_name = data_dict["device"]["uram"][0]["uram_name"]

        data_device_conf = {'mix': 2, 'any': 1}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                    spare=spare_drives, raid_type="RAID5",
                                    array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )