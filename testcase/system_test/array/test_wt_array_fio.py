import pytest
import traceback

from pos import POS
import logger
import random
import time

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("wt_array.json")
    data_dict = pos.data_dict
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

def wt_test_setup_function(array_name: str, raid_type: str, nr_data_drives: int):
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives):
            pytest.skip(f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}")
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = []

        if raid_type.upper() == "NORAID":
            raid_type = "no-raid"

        assert pos.cli.create_array(write_buffer="uram0", data=data_disk_list,
                                    spare=spare_disk_list, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True

        return True
    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False

@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives", 
                        [("NORAID", 1), ("RAID0", 2), ("RAID5", 3),
                         ("RAID10", 2), ("RAID10", 4)])
def test_wt_array_block_file_FIO(raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_block_file_FIO ================== "
    )
    try:
        array_name = "array1"
        vol_size = '2200mb'     # Volume Size
        io_size = '2g'      # FIO IO size
        if raid_type in ("NORAID", "RAID10") and nr_data_drives <= 2:
            vol_size = '1200mb'
            io_size = '1g'

        assert wt_test_setup_function(array_name, raid_type, nr_data_drives) == True

        assert pos.target_utils.create_volume_multiple(array_name, 256, "pos_vol",
                                                    size=vol_size) == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem1" in ss]
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                            volume_list=pos.cli.vols, nqn_list=ss_list) == True

        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss,
                            pos.target_utils.helper.ip_addr[0], "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                    --iodepth=64 --direct=1 --bs=128k --size={io_size}"
        
        file_io_devs = nvme_devs[0:128]
        block_io_devs = nvme_devs[128:256]
        assert pos.client.create_File_system(file_io_devs, fs_format="xfs")
        out, mount_point = pos.client.mount_FS(file_io_devs)
        assert out == True 
        io_mode = False     # Set False this to File IO
        out, async_file_io = pos.client.fio_generic_runner(mount_point, 
                    fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)
        assert out == True

        io_mode = True      # Set False this to Block IO
        out, async_block_io = pos.client.fio_generic_runner(block_io_devs,
                     fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)
        assert out == True

        # Wait for async FIO completions
        while True:
            time.sleep(30)          # Wait for 30 seconds
            file_io =  async_file_io.is_complete()
            block_io = async_block_io.is_complete()

            msg = []
            if not file_io:
                msg.append("File IO")
            if not block_io:
                msg.append("Block IO")

            if msg:
                logger.info("'{}' is still running. Wait 30 seconds...".format(
                                ",".join(msg)))
                continue
            break
        #assert pos.client.delete_FS(mount_point) == True
        assert pos.client.unmount_FS(mount_point) == True
        
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        assert pos.client.unmount_FS(mount_point) == True
        pos.exit_handler(expected=False)