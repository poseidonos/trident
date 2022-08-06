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


array = [("RAID5", 3),]

@pytest.mark.regression
@pytest.mark.parametrize("repeat_ops", [5])
@pytest.mark.parametrize("raid_type, num_devs", array)
def test_hetero_multi_array_npor_mounted_array(raid_type, num_devs, repeat_ops):
    """
    Create and mount two RAID5 (Default) arrays using 3 (default) number of hetero devices.
    Peform NPOR and verify array are mounted. Unmount and delete arrays. Repeat 5 times.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_npor_mounted_array ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        for i in range(repeat_ops):
            num_array = 2
            # Create two RAID array of specified RAID using hetero devices.
            for id in range(num_array):
                assert pos.cli.scan_device()[0] == True
                assert pos.cli.list_device()[0] == True

                # Verify the minimum disk requirement
                if len(pos.cli.system_disks) < (num_array - id) * num_devs:
                    pytest.skip(f"Insufficient disk {len(pos.cli.system_disks)}. "\
                                f"Required minimum {(num_array - id) * num_devs}")

                array_name = f"array{id+1}"
                raid_type = raid_type
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
                assert pos.cli.info_array(array_name=array_name)[0] == True

            assert pos.target_utils.Npor() == True

            assert pos.cli.list_array()[0] == True
            for array in pos.cli.array_dict.keys():
                assert pos.cli.info_array(array_name=array)[0] == True
                if pos.cli.array_dict[array].lower() == "mounted":
                    assert pos.cli.unmount_array(array_name=array)[0] == True
                assert pos.cli.delete_array(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
@pytest.mark.parametrize("array_raid, num_devs", array)
def test_hetero_array_spor(array_raid, num_devs):
    """
    Test create single array of selected raid type and num of disk using hetero 
    devices. Run IO and do SPOR. 
    """
    logger.info(
        " ==================== Test : test_hetero_array_spor ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        # Verify the minimum disk requirement
        if len(pos.cli.system_disks) < num_devs:
            pytest.skip(f"Insufficient disk {len(pos.cli.system_disks)}. "\
                        f"Required minimum {num_devs}")

        array_name = "array1"
        uram_name = data_dict["device"]["uram"][0]["uram_name"]

        if array_raid.lower() == "raid0" and num_devs == 2:
            data_device_conf = {'mix': 2}
        else:
            data_device_conf = {'mix': 2, 'any': num_devs - 2}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                    spare=spare_drives, raid_type=array_raid,
                                    array_name=array_name)[0] == True

        assert pos.cli.mount_array(array_name=array_name)[0] == True
        assert pos.cli.info_array(array_name=array_name)[0] == True

        array_size = int(pos.cli.array_info[array_name].get("size"))
        vol_size = f"{int(array_size / (1024 * 1024))}mb"  # Volume Size in MB
        vol_name = "pos_vol"

        assert pos.cli.create_volume(vol_name, array_name=array_name,
                                    size=vol_size)[0] == True

        assert pos.target_utils.get_subsystems_list() == True
        nqn = pos.target_utils.ss_temp_list[0]
        assert pos.cli.mount_volume(vol_name, array_name, nqn)[0] == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True
        assert pos.client.nvme_list() == True

        fio_cmd  = f"fio --name=seq_write --ioengine=libaio --rw=write "\
                   f"--iodepth=64 --direct=1 --numjobs=1 --bs=128k "\
                   f"--time_based --runtime=120",

        assert pos.client.fio_generic_runner(pos.client.nvme_list_out,
                fio_user_data=fio_cmd)[0] == True

        assert pos.target_utils.Spor(uram_backup=False) == True
        
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
@pytest.mark.parametrize("fio_runtime", [120])
@pytest.mark.parametrize("array_raid, num_devs", array)
def test_hetero_multi_array_spor(array_raid, num_devs, fio_runtime):
    """
    Test to create multi arrays of selected raid type and num of disk using hetero 
    devices. Run IO and do SPOR. 
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_spor ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list

        # Create two RAID array of RAID5 using hetero device
        num_array = 2
        for id in range(num_array):
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < (num_array - id) * num_devs:
                pytest.skip(f"Insufficient disks {len(pos.cli.system_disks)}. "\
                            f"Required minimum {(num_array - id) * num_devs}")

            array_name = f"array{id+1}"
            uram_name = data_dict["device"]["uram"][id]["uram_name"]

            if array_raid.lower() == "raid0" and num_devs == 2:
                data_device_conf = {'mix': 2}
            else:
                data_device_conf = {'mix': 2, 'any': num_devs - 2}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type=array_raid,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_info[array_name].get("size"))
            vol_size = f"{int(array_size / (1024 * 1024))}mb"  # Volume Size in MB
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.create_volume(vol_name, vol_size, 
                                         array_name=array_name)[0] == True

            nqn = ss_list[id]
            assert pos.cli.mount_volume(vol_name, array_name, nqn)[0] == True

            # Connect client
            ip_addr = pos.target_utils.helper.ip_addr[0]
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True
        
        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run Block IO
        fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write "\
                  f"--bs=128k --time_based --runtime={fio_runtime} "\
                  f"--size={vol_size}"

        assert pos.client.fio_generic_runner(
                nvme_devs, fio_user_data=fio_cmd, IO_mode=True) == True

        assert pos.target_utils.Spor() == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )