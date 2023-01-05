from array import array
import pytest
import random
from pos import POS
from common_libs import *
import json
import os
import time

import logger
logger = logger.get_logger(__name__)


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
def test_wt_array_rebuild_after_FIO(
    setup_cleanup_array_function, raid_type, nr_data_drives, file_io
):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert wt_array_volume_setup(pos, raid_type, nr_data_drives, 1) == True
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

        assert pos.cli.array_info(array_name=array_name)[0] == True
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
def test_wt_array_rebuild_during_FIO(
    setup_cleanup_array_function, raid_type, nr_data_drives, file_io
):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert wt_array_volume_setup(pos, raid_type, nr_data_drives, 1) == True
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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

        assert pos.cli.array_info(array_name=array_name)[0] == True
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
