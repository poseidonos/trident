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


array = [("RAID5", 3)]

@pytest.mark.regression
@pytest.mark.parametrize("array_raid, num_devs", array)
def test_hetero_multi_array_smart_log(array_raid, num_devs):
    """
    Test to create two RAID5 (Default) arrays with 3 (Default) hetero devices.
    Create and mount 100 volumes from each array. Trigger GC.
    """
    logger.info(
        " ==================== Test :  test_hetero_multi_array_GC ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        num_array = 2
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:num_array]
        for id in range(num_array):
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < (num_array - id) * num_devs:
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {(num_array - id) * num_devs}")

            array_name = f"array{id+1}"
            raid_type = array_raid
            uram_name = data_dict["device"]["uram"][id]["uram_name"]

            if raid_type.lower() == "raid0" and num_devs == 2:
                data_device_conf = {'mix': 2}
            else:
                data_device_conf = {'mix': 2, 'any': num_devs - 2}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True

        assert pos.cli.list_array()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.info_array(array_name=array_name)[0] == True
            for device in pos.cli.array_info[array_name]["data_list"]:
                assert pos.cli.smart_log_device(devicename=device)[0] == True


    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )