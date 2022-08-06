from timeit import repeat
import pytest
import traceback

from pos import POS
import logger
import time
import random

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, min_hetero_dev
    pos = POS("pos_config.json")

    data_dict = pos.data_dict
    data_dict["subsystem"]["nr_subsystems"] = 1023
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


array = [("RAID5", 12)]
@pytest.mark.parametrize("raid_type, num_disk", array)
def test_hetero_multi_array_512_vols_1024_subs_FIO(raid_type, num_disk):
    """
    Test two RAID5 arrays using hetero devices, Create 256 volumes on each array.
    mount array to different unique subsystem. Run mix of File and Block FIO.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_512_vols_1024_subs_FIO ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True
        assert pos.target_utils.get_subsystems_list() == True

        repeat = 10
        num_array = 2
        num_vols = 256
        fio_runtime = 5  # FIO for 2 minutes
        ss_list_temp = pos.target_utils.ss_temp_list[:]

        for id in range(repeat):
            random.shuffle(ss_list_temp)
            nqn_list = ss_list_temp[:2*num_vols]
            nqn_array_list = [nqn_list[:num_vols], nqn_list[num_vols:2*num_vols]]
    
            for id in range(num_array):
                assert pos.cli.scan_device()[0] == True
                assert pos.cli.list_device()[0] == True

                # Verify the minimum disk requirement
                if len(pos.cli.system_disks) < (num_array - id) * num_disk:
                    pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                                f"Required minimum {(num_array - id) * num_disk}")

                array_name = f"array{id+1}"
                uram_name = data_dict["device"]["uram"][id]["uram_name"]

                if raid_type.lower() == "raid0" and num_disk == 2:
                    data_device_conf = {'mix': 2}
                else:
                    data_device_conf = {'mix': 2, 'any': num_disk - 2}

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

                array_size = int(pos.cli.array_info[array_name].get("size"))
                vol_size = f"{int(array_size / (1024 * 1024) / num_vols)}mb"  # Volume Size in MB
                vol_name = "pos_vol"

                assert pos.target_utils.create_volume_multiple(array_name, num_vols,
                        vol_name=vol_name, size=vol_size, maxiops=0, bw=0) == True

                assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                                volume_list=pos.cli.vols, nqn_list=nqn_array_list[id]) == True

            # Connect client
            for nqn in nqn_list():
                assert pos.client.nvme_connect(nqn, 
                        pos.target_utils.helper.ip_addr[0], "1158") == True
            
            assert pos.client.nvme_list() == True

            # Run File IO or Block IO
            fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write --bs=128k "\
                    f"--iodepth=64 --time_based --runtime={fio_runtime} --size={vol_size}"

            # Run IO to only 128 devices attached to 1 Initiator 
            nvme_dev_list = pos.client.nvme_list_out[:128]
            random.shuffle(nvme_dev_list)
            file_io_devs = nvme_dev_list[:64]
            # File IO
            assert pos.client.create_File_system(file_io_devs, fs_format="xfs")
            out, mount_point = pos.client.mount_FS(file_io_devs)
            assert out == True
            io_mode = True  # Set True for File IO

            out, async_file_io = pos.client.fio_generic_runner(mount_point,
                    fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)
            assert out == True

            # Block IO
            block_io_devs = nvme_dev_list[64:]
            io_mode = False  # Set False for Block IO
            out, async_block_io = pos.client.fio_generic_runner(block_io_devs,
                    fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)

            # Wait for async FIO completions
            while True:
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

            # Delete Array In Reverse Order
            assert pos.cli.list_array()[0] == True
            array_list = pos.cli.array_dict.keys()
            for array in array_list:
                assert pos.cli.list_volume(array_name=array)[0] == True
                for vol in pos.cli.vols[::-1]:
                    assert pos.cli.unmount_volume(vol, array_name=array)[0] == True
                    assert pos.cli.delete_volume(vol, array_name=array)[0] == True

                assert pos.cli.unmount_array(array_name=array)[0] == True
                assert pos.cli.delete_array(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
    
    logger.info(
        " ============================= Test ENDs ======================================"
    )