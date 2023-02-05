import pytest
import traceback

import logger

logger = logger.get_logger(__name__)

# Global veriable to verify hetero setup requirement
MIN_HETERO_DEV = 1
MIN_16_NS_DEV = 1

@pytest.fixture(scope="function")
def hetero_setup(system_fixture):

    global data_dict, min_hetero_dev
    pos = system_fixture

    # TODO replace with relative path
    tgt_setup_file = "hetero_setup.json"
    conf_dir = "../../config_files/"

    data_path = f"{conf_dir}{tgt_setup_file}"
    tgt_conf_data = pos._json_reader(data_path, abs_path=True)[1]
    
    if tgt_conf_data["enable"] == "false":
        logger.warning("The enable flag is not true in hetero_setup.json file."
                       "The hetero setup creation will be skipped.")
    
    min_hetero_dev = MIN_HETERO_DEV
    if (min_hetero_dev < tgt_conf_data["num_test_device"]):
        logger.warning("The setup required minimum {} Hetero devices. "
                        "Only {} Hetero devices is added in config file".format(
                        min_hetero_dev, tgt_conf_data["num_test_device"]))
        pytest.skip("Required condition not met. Refer to logs for more details")

    # Atleast 1 device with 16 NS
    matched = 0
    min_16ns_dev = MIN_16_NS_DEV
    for device in range(tgt_conf_data["test_devices"]):
        ns_count = sum([ns["num_namespace"] for ns in device["ns_config"]])
        if ns_count >= 16:    # If Num of NS of a drive more than 16
            matched += 1

    if matched < min_16ns_dev:
        logger.warning("The setup required atleast {} devices with 16 Namespaces. "
                    "{} device(s) is/are added in config file".format(
                        min_16ns_dev, matched))
        pytest.skip("Required condition not met. Refer to logs for more details")

    assert pos.target_utils.hetero_setup.prepare(tgt_conf_data) == True

    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    yield pos

    logger.info("========== TEAR DOWN AFTER TEST =========")
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.pos_stop()[0] == True
    assert pos.target_utils.hetero_setup.reset() == True


@pytest.mark.hetero_setup
@pytest.mark.regression
def test_hetero_array_all_raid(hetero_setup):
    """
    Test to create one array of all RAID type using minimum required devices of 
    different size. Atleast one device of size 20 GiB.
    """
    logger.info(
        " ==================== Test : test_hetero_array_all_raid ================== "
    )
    try:
        pos = hetero_setup
        array_name = "array1"
        uram_name = data_dict["device"]["uram"][0]["uram_name"]

        raid_list = [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 4)]
        for raid_type, num_disk in raid_list:
            assert pos.cli.devel_resetmbr()[0] == True
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True

            if len(pos.cli.system_disks) < num_disk:
                logger.warning("Avilable drive {} is insufficient, required {}".format(
                    num_disk, len(pos.cli.system_disks)))

            data_device_conf = {'20GiB':1, 'any':num_disk-1}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type=raid_type,
                                        array_name=array_name)[0] == True
            
            assert pos.cli.array_mount(array_name=array_name, write_back=False)[0] == True

            assert pos.cli.array_unmount(array_name=array_name)[0] == True

            assert pos.cli.array_delete(array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
