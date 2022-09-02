import pytest
import traceback

from pos import POS
import logger

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, min_hetero_dev
    pos = POS("pos_config.json")

    tgt_setup_file = "hetero_setup.json"
    conf_dir = "../../config_files/"

    data_path = f"{conf_dir}{tgt_setup_file}"
    tgt_conf_data = pos._json_reader(data_path, abs_path=True)[1]
    
    if tgt_conf_data["enable"] == "false":
        logger.warning("The enable flag is not true in hetero_setup.json file."
                       "The hetero setup creation will be skipped.")
    
    min_hetero_dev = 1
    if (min_hetero_dev > tgt_conf_data["num_test_device"]):
        logger.warning("The setup required minimum {} Hetero devices. "
                        "Only {} Hetero devices is added in config file".format(
                        min_hetero_dev, tgt_conf_data["num_test_device"]))
        pytest.skip("Required condition not met. Refer to logs for more details")

    # Atleast 1 device of size 20 GiB
    matched = 0
    min_20gib_dev = 1
    for index in range(tgt_conf_data["num_test_device"]):
        dev = tgt_conf_data["test_devices"][index]
        if dev["ns_config"][0]["ns_size"] == "20GiB":
            matched += 1

    if matched < min_20gib_dev:
        logger.warning("The setup required atleast {} 20 GiB devices. "
                    "{} device(s) is/are added in config file".format(
                        min_20gib_dev, matched))
        pytest.skip("Required condition not met. Refer to logs for more details")

    assert pos.target_utils.hetero_setup.prepare(tgt_conf_data) == True

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
            assert pos.cli.delete_array(array_name=array)[0] == True
        
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

array = [("RAID0",2), ("RAID5",3), ("RAID10",4)]
@pytest.mark.hetero_setup
@pytest.mark.regression
@pytest.mark.parametrize("raid_type,num_disk", array)
def test_hetero_array_all_raid(raid_type,num_disk):
    """
    Test to create one array of all RAID type using minimum required devices of 
    different size. Atleast one device of size 20 GiB.
    """
    logger.info(
        " ==================== Test : test_hetero_array_all_raid ================== "
    )
    try:
        array_name = "array1"
        uram_name = data_dict["device"]["uram"][0]["uram_name"]
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < num_disk:
            logger.warning("Avilable drive {} is insufficient, required {}".format(
                num_disk, len(pos.cli.system_disks)))

        data_device_conf = {'20GiB':1, 'any':num_disk-1}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                    spare=spare_drives, raid_type=raid_type,
                                    array_name=array_name)[0] == True
        
        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True

        assert pos.cli.unmount_array(array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.hetero_setup
@pytest.mark.regression
@pytest.mark.parametrize("mount_type", ["WT", "WB"])
@pytest.mark.parametrize("raid_type", ["RAID0", "RAID5", "RAID10"])
def test_hetero_array_all_dev_fio(raid_type, mount_type):
    """
    Test to create one array of all RAID type using all available devices of 
    different size. Atleast one device of size 20 GiB.
    """
    logger.info(
        " ==================== Test : test_hetero_array_all_dev_fio ================== "
    )
    try:
        array_name = "array1"
        assert pos.cli.list_device()[0] == True
        uram_name = data_dict["device"]["uram"][0]["uram_name"]
        data_device_conf = {'any': len(pos.cli.system_disks)}

        if raid_type != "RAID5":
            if len(pos.cli.system_disks) % 2 != 0:
                data_device_conf = {'20giB':1, 'any': len(pos.cli.system_disks) - 2}
            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type=raid_type,
                                        array_name=array_name)[0] == True

        write_back = False if mount_type == 'WT' else True
            
        assert pos.cli.mount_array(array_name=array_name, write_back=write_back)[0] == True
        assert pos.cli.info_array(array_name=array_name)[0] == True
        array_size = int(pos.cli.array_info[array_name].get("size"))
        vol_size = f"{int(array_size // (1024 * 1024))}mb"  # Volume Size in MB

        assert pos.target_utils.create_volume_multiple(array_name, 1, 
                                "pos_vol", size=vol_size) == True

        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_temp_list = pos.target_utils.ss_temp_list
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                volume_list=pos.cli.vols, nqn_list=ss_temp_list) == True

        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, 
                pos.target_utils.helper.ip_addr[0], "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run Block IO
        fio_cmd = "fio --name=random_write --ioengine=libaio --rw=randwrite "\
                "--iodepth=64 --direct=1 --bs=128k --time_based --runtime=5"

        assert pos.client.fio_generic_runner(nvme_devs,
                                    fio_user_data=fio_cmd)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )