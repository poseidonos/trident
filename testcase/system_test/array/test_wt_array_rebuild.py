import pytest

import traceback

from pos import POS
import logger
import random
import time

# from pos import POS

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict['array']['phase'] = "false"
    data_dict['volume']['phase'] = "false"
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

    assert pos.target_utils.pci_rescan() == True

    # assert pos.cli.reset_devel()[0] == True
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
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = [system_disks.pop()]

        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=spare_disk_list,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )

        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True
        assert (
            pos.cli.create_volume("pos_vol1", array_name=array_name, size="1000gb")[0]
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem1" in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        return True
    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives, file_io",
    [
        ("RAID5", 3, True),
        ("RAID5", 3, False),
        ("RAID10", 2, True),
        ("RAID10", 2, False),
        ("RAID10", 4, True),
        ("RAID10", 4, False),
    ],
)
def test_wt_array_rebuild_after_FIO(raid_type, nr_data_drives, file_io):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        array_name = "array1"
        assert wt_test_setup_function(array_name, raid_type, nr_data_drives) == True
        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out
        if file_io:
            assert pos.client.create_File_system(nvme_devs, fs_format="xfs")
            out, mount_point = pos.client.mount_FS(nvme_devs)
            assert out == True
            device_list = mount_point
            io_mode = False  # Set False this to File IO
        else:
            device_list = pos.client.nvme_list_out
            io_mode = True  # Set False this to Block IO

        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --bs=128k --time_based --runtime=120 --size=100g"
        assert (
            pos.client.fio_generic_runner(
                device_list, fio_user_data=fio_cmd, IO_mode=io_mode
            )[0]
            == True
        )

        assert pos.cli.info_array(array_name=array_name)[0] == True
        remove_drives = [random.choice(pos.cli.array_info[array_name]["data_list"])]
        assert pos.target_utils.device_hot_remove(device_list=remove_drives)
        assert pos.target_utils.array_rebuild_wait(array_name=array_name)

        if file_io:
            assert pos.client.delete_FS(mount_point) == True
            assert pos.client.unmount_FS(mount_point) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        if file_io:
            assert pos.client.delete_FS(mount_point) == True
            assert pos.client.unmount_FS(mount_point) == True
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives, file_io",
    [
        ("RAID5", 3, True),
        ("RAID5", 3, False),
        ("RAID10", 2, True),
        ("RAID10", 2, False),
        ("RAID10", 4, True),
        ("RAID10", 4, False),
    ],
)
def test_wt_array_rebuild_during_FIO(raid_type, nr_data_drives, file_io):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        array_name = "array1"
        assert wt_test_setup_function(array_name, raid_type, nr_data_drives) == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out
        if file_io:
            assert pos.client.create_File_system(nvme_devs, fs_format="xfs")
            out, mount_point = pos.client.mount_FS(nvme_devs)
            assert out == True
            device_list = mount_point
            io_mode = False  # Set False this to File IO
        else:
            device_list = nvme_devs
            io_mode = True  # Set False this to Block IO

        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=8 --bs=128k --time_based --runtime=300 --size=100g"
        res, async_out = pos.client.fio_generic_runner(
            device_list, IO_mode=io_mode, fio_user_data=fio_cmd, run_async=True
        )
        assert res == True

        time.sleep(180)  # Run IO for 3 minutes before Hot Remove

        assert pos.cli.info_array(array_name=array_name)[0] == True
        remove_drives = [random.choice(pos.cli.array_info[array_name]["data_list"])]
        assert pos.target_utils.device_hot_remove(device_list=remove_drives)
        assert pos.target_utils.array_rebuild_wait(array_name=array_name)

        # Wait for async FIO completions
        while async_out.is_complete() == False:
            logger.info("FIO is still running. Wait 30 seconds...")
            time.sleep(30)

        if file_io:
            assert pos.client.delete_FS(mount_point) == True
            assert pos.client.unmount_FS(mount_point) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        if file_io:
            assert pos.client.delete_FS(mount_point) == True
            assert pos.client.unmount_FS(mount_point) == True
        pos.exit_handler(expected=False)
