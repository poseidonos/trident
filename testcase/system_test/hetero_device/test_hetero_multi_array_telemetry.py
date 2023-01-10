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

    assert pos.cli.array_list()[0] == True
    for array in pos.cli.array_dict.keys():
        assert pos.cli.array_info(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


array = [("RAID5", 3)]

@pytest.mark.regression
@pytest.mark.parametrize("array_raid, num_devs", array)
def test_hetero_multi_array_telemetry(array_raid, num_devs):
    """
    Test to create two RAID5 (Default) arrays with 3 (Default) hetero devices.
    Create and mount 100 volumes from each array. Start Telemetry. 
    Run Block IO for 5 minutes. Stop Telemery.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_telemetry ================== "
    )
    try:
        assert pos.cli.devel_resetmbr()[0] == True

        repeat_ops=5
        num_array = 2
        num_vols = 100
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:num_array]
        for counter in range(repeat_ops):
            logger.info(f"Start of {counter+1}/{repeat_ops} Execution!")
            for id in range(num_array):
                assert pos.cli.device_scan()[0] == True
                assert pos.cli.device_list()[0] == True

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

                assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                            spare=spare_drives, raid_type=raid_type,
                                            array_name=array_name)[0] == True

                assert pos.cli.array_mount(array_name=array_name)[0] == True
                assert pos.cli.array_info(array_name=array_name)[0] == True 

                array_size = int(pos.cli.array_data[array_name].get("size"))
                vol_size = f"{int((array_size / num_vols) / (1024 * 1024))}mb"
                vol_name = "pos_vol"

                assert pos.target_utils.create_volume_multiple(array_name, num_vols,
                        vol_name=vol_name, size=vol_size, maxiops=0, bw=0) == True

                nqn=ss_list[id]
                assert pos.cli.volume_list(array_name=array_name)[0] == True
                assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                                volume_list=pos.cli.vols, nqn_list=[nqn]) == True

                # Connect client
                assert pos.client.nvme_connect(nqn, 
                        pos.target_utils.helper.ip_addr[0], "1158") == True

            assert pos.cli.telemetry_start()[0] == True

            assert pos.client.nvme_list() == True
            run_time = 5  # FIO for 5 minutes

            # Block IO
            fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write "\
                      f"--bs=128k --iodepth=64 --time_based --runtime={run_time}"

            io_mode = False  # Set False for Block IO
            assert pos.client.fio_generic_runner(pos.client.nvme_list_out,
                                    fio_user_data=fio_cmd, IO_mode=io_mode)

            assert pos.cli.telemetry_stop()[0] == True

            assert pos.cli.array_list()[0] == True
            for array in pos.cli.array_dict.keys():
                assert pos.cli.array_unmount(array_name=array)[0] == True
                assert pos.cli.array_delete(array_name=array)[0] == True

            logger.info(f"End of {counter+1}/{repeat_ops} Execution!")

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
