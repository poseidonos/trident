import pytest
import traceback

from pos import POS
import logger
import time 

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
    array_list = list(pos.cli.array_dict.keys())
    for array in array_list:
        assert pos.cli.info_array(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.delete_array(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

array_raid_disk = [("RAID0", 2), ("RAID0", 4), ("RAID5", 3), ("RAID10", 4), ("RAID5", 16)]
array_mount_type = ["WT", "WB"]
fio_io_type = ["block", "file"]

@pytest.mark.regression
@pytest.mark.parametrize("fio_runtime", ["60", "120"])
@pytest.mark.parametrize("io_type", fio_io_type)
@pytest.mark.parametrize("array2_mount", array_mount_type)
@pytest.mark.parametrize("array2_raid, array2_devs", array_raid_disk)
@pytest.mark.parametrize("array1_mount", array_mount_type)
@pytest.mark.parametrize("array1_raid, array1_devs", array_raid_disk)
def test_hetero_multi_array_max_size_volume_FIO(
                        array1_raid, array1_devs, array1_mount,
                        array2_raid, array2_devs, array2_mount, 
                        io_type, fio_runtime):
    """
    Test two arrays using hetero devices, Create max size volume on each array.
    Run File or Block FIO.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_max_size_volume_FIO ================== "
    )
    try:
        mount_point = None
        io_mode = True
        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list
        raid_types = (array1_raid, array2_raid)
        num_devs = (array1_devs, array2_devs)
        mount_types = (array1_mount, array2_mount)

        for id in range(2):
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < sum(num_devs[id:]):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {sum(num_devs)}")

            array_name = f"array{id+1}"
            raid_type = raid_types[id]
            num_devices = num_devs[id]
            mount_type = mount_types[id]
            uram_name = data_dict["device"]["uram"][id]["uram_name"]

            if raid_type.lower() == "raid0" and num_devices == 2:
                data_device_conf = {'mix': 2}
            else:
                data_device_conf = {'mix': 2, 'any': num_devices - 2}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            if (mount_type == "wt"):
                write_back=False
            else:
                write_back=True
                if (mount_type != "wb"):
                    logger.warning("Unsupported mount type. Use default Write Back")

            assert pos.cli.mount_array(array_name=array_name, 
                                       write_back=write_back)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_info[array_name].get("size"))
            vol_size = f"{array_size // (1024 * 1024)}mb"  # Volume Size in MB
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.create_volume(vol_name, vol_size, array_name=array_name)[0] == True

            ss_list = [ss for ss in ss_temp_list if f"array{id + 1}" in ss]
            nqn=ss_list[0]
            assert pos.cli.mount_volume(vol_name, array_name, nqn)[0] == True

            # Connect client
            assert pos.client.nvme_connect(nqn, 
                    pos.target_utils.helper.ip_addr[0], "1158") == True
        
        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run File IO or Block IO
        fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write --bs=128k "\
                  f"--iodepth=64 --time_based --runtime={fio_runtime} --size={vol_size}"

        if (io_type == "file"):
            assert pos.client.create_File_system(nvme_devs, fs_format="xfs")
            out, mount_point = pos.client.mount_FS(nvme_devs)
            assert out == True
            io_mode = False     # Set False this to File IO
            nvme_devs = mount_point

        assert pos.client.fio_generic_runner(
                    nvme_devs, fio_user_data=fio_cmd, IO_mode=io_mode)[0] == True
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
            mount_point = None

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


array = [("RAID5", 3)]
@pytest.mark.parametrize("additional_ops", ["no", "npor", "vol_del_reverse"])
@pytest.mark.parametrize("raid_type, num_disk", array)
def test_hetero_multi_array_512_volume_mix_FIO(raid_type, num_disk, additional_ops):
    """
    Test two RAID5 arrays using hetero devices, Create 256 volumes on each array.
    Run File and Block FIO.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_512_volume_mix_FIO ================== "
    )
    try:
        assert pos.target_utils.get_subsystems_list() == True

        repeat_ops = 1 if additional_ops == "no" else 5
        num_array = 2
        num_vols = 256
        fio_runtime = 120  # FIO for 2 minutes
        ss_list = pos.target_utils.ss_temp_list[:num_array]

        for counter in range(repeat_ops):
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

                nqn=ss_list[id]
                assert pos.cli.list_volume(array_name=array_name)[0] == True
                assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                                volume_list=pos.cli.vols, nqn_list=[nqn]) == True

                # Connect client
                assert pos.client.nvme_connect(nqn, 
                        pos.target_utils.helper.ip_addr[0], "1158") == True
            
            assert pos.client.nvme_list() == True
            nvme_devs = pos.client.nvme_list_out

            # Run File IO or Block IO
            fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write --bs=128k "\
                    f"--iodepth=64 --time_based --runtime={fio_runtime} --size={vol_size}"

            nr_dev = 64
            for i in range(len(nvme_devs) // nr_dev):
                nvme_dev_list = nvme_devs[i * nr_dev : (i + 1) * nr_dev]
                file_io_devs = nvme_dev_list[:32]
                # File IO
                mount_point = None
                assert pos.client.create_File_system(file_io_devs, fs_format="xfs")
                out, mount_point = pos.client.mount_FS(file_io_devs)
                assert out == True
                io_mode = True  # Set True for File IO
  
                out, async_file_io = pos.client.fio_generic_runner(mount_point,
                        fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)
                assert out == True

                # Block IO
                block_io_devs = nvme_dev_list[32:]
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

                if mount_point:
                    assert pos.client.unmount_FS(mount_point) == True

            if repeat_ops > 1:
                if pos.client.ctrlr_list()[1]:
                    assert pos.client.nvme_disconnect(ss_list) == True
                assert pos.cli.list_array()[0] == True
                if additional_ops == "npor":
                    # Perform NPOR
                    assert pos.target_utils.Npor() == True
                elif additional_ops == "vol_del_reverse" :
                    for array in pos.cli.array_dict.keys():
                        # Delete volumes in reverse order
                        assert pos.cli.list_volume(array_name=array)[0] == True
                        for vol in pos.cli.vols[::-1]:
                            assert pos.cli.unmount_volume(vol, array_name=array)[0] == True
                            assert pos.cli.delete_volume(vol, array_name=array)[0] == True
                # Delete bot array Array     
                for array in pos.cli.array_dict.keys():
                    assert pos.cli.unmount_array(array_name=array)[0] == True
                    assert pos.cli.delete_array(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)
    
    logger.info(
        " ============================= Test ENDs ======================================"
    )