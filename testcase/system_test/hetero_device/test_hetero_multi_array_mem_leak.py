
import pytest
import traceback

from pos import POS
import logger
import time 
import re

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, min_hetero_dev
    pos = POS("pos_config.json")

    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    assert pos.cli.reset_devel()[0] == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    for array in pos.cli.array_dict.keys():
        assert pos.cli.info_array(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.delete_array(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


array_raid_disk = [("RAID5", 12)]

@pytest.mark.regression
@pytest.mark.parametrize("raid_type, num_devs", array_raid_disk)
def test_hetero_multi_array_long_io_mem_leak(raid_type, num_devs):
    """
    Create two RAID5 (Default) arrays using 12 (default) hetero devices. 
    Create two volumes to utilize max capacity of each array. Run overnight
    File and Block FIO.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_long_io_mem_leak ================== "
    )
    try:
        num_arrays = 2

        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:num_arrays]

        for id in range(num_arrays):
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < (num_arrays - id) * num_devs:
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {(num_arrays - id) * num_devs}")

            array_name = f"array{id+1}"
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

            assert pos.cli.mount_array(array_name=array_name, 
                                       write_back=True)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_info[array_name].get("size"))
            num_vols = 2
            vol_size = f"{int((array_size / 2) / (1024 * 1024))}mb"  # Volume Size in MB

            for vol_id in range(num_vols):
                vol_name = f"{array_name}_pos_vol{vol_id}"
                assert pos.cli.create_volume(vol_name, vol_size, 
                                                array_name=array_name)[0] == True

                nqn=ss_list[id]
                assert pos.cli.mount_volume(vol_name, array_name, nqn)[0] == True

            # Connect client
            assert pos.client.nvme_connect(nqn, 
                                pos.target_utils.helper.ip_addr[0], "1158") == True
        
        assert pos.client.nvme_list() == True

        nvme_devs = pos.client.nvme_list_out

        # Run File IO or Block IO
        fio_runtime = 60 * 60 * 1 # 1 hours
        fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write --bs=128k "\
                  f"--iodepth=64 --time_based --runtime={fio_runtime} --size={vol_size}"

        file_io_devs = nvme_devs[:2]
        # File IO
        assert pos.client.create_File_system(file_io_devs, fs_format="xfs")
        out, mount_point = pos.client.mount_FS(file_io_devs)
        assert out == True
        io_mode = True  # Set True for File IO

        out, async_file_io = pos.client.fio_generic_runner(mount_point,
                fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)
        assert out == True

        # Block IO
        block_io_devs = nvme_devs[2:]
        io_mode = False  # Set False for Block IO
        out, async_block_io = pos.client.fio_generic_runner(block_io_devs,
                fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)

        # Wait for async FIO completions
        while True:
            assert pos.target_utils.helper.check_system_memory() == True
            time.sleep(30)  # Wait for 30 seconds
            msg = []
            if not async_file_io.is_complete():
                msg.append("File IO")
            if not async_block_io.is_complete():
                msg.append("Block IO")
            if msg:
                logger.info(f"{','.join(msg)} is still running. Wait 30 seconds...")
                continue
            break

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )