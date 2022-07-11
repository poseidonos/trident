import pytest

from pos import POS
import logger
import random
import time

# from pos import POS

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():
    global pos, data_dict
    pos = POS("wt_array.json")
    data_dict = pos.data_dict
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
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

    assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives",
                         [("RAID0", 2)])
def test_wt_array_io_spor(raid_type, nr_data_drives):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(
        " ==================== Test : test_wt_array_io_spor ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}")

        assert pos.target_utils.get_subsystems_list() == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem" in ss]

        array_name = "posarray0"
        uram = 'uram0'
        # Create array1, volume and mount in WT
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        assert pos.cli.create_array(write_buffer=uram, data=data_disk_list,
                                    spare=None, raid_type=raid_type,
                                    array_name=array_name)[0] == True
        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True
        assert pos.cli.create_volume("pos_vol1", array_name=array_name, size="2000gb")[0] == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                                                      volume_list=pos.cli.vols, nqn_list=ss_list) == True

        # Connect client
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss,
                                           pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True

        # Run IO
        pos.client.check_system_memory()
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                            --iodepth=64 --direct=1 --bs=128k --size=100%"

        block_io_devs = nvme_devs
        io_mode = True  # Set False this to Block IO
        out, async_block_io = pos.client.fio_generic_runner(block_io_devs,
                                                            fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True)
        assert out == True

        # Wait for async FIO completions
        while True:
            time.sleep(30)  # Wait for 30 seconds
            block_io = async_block_io.is_complete()

            msg = []
            if not block_io:
                msg.append("Block IO")

            if msg:
                logger.info("'{}' is still running. Wait 30 seconds...".format(
                    ",".join(msg)))
                continue
            break

        # Perfrom SPOR
        assert pos.target_utils.Spor(uram_backup=False) == True

        pos.client.check_system_memory()
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
