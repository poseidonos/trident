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

    data_dict["device"]["phase"] = "false"
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
def test_hetero_three_raid5_array():
    """
    Test auto create arrays of no-raid with different NUMA node
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        # Loop 3 times to create two RAID array of RAID5 using hetero device
        for id in range(3):
            uram_name=f"uram{id}"
            array_name = f"array{id+1}"

            assert pos.cli.create_device(uram_name=uram_name, bufer_size="8388608",
                                         strip_size="512", numa="1")[0] == True
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (3 - id):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (3 - id)} disk to create array")

            data_device_conf = {'mix': 2, 'any': 1}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            # The 3rd array creation should fail.  
            res = False if(id == 2) else True

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == res

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )
