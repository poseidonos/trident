from array import array
import pytest

import logger as logging
import time
import pprint
from common_libs import *

logger = logging.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_wt_array_block_file_FIO(
    array_fixture, raid_type, nr_data_drives
):
    logger.info(
        " ==================== Test : test_wt_array_block_file_FIO ================== "
    )
    try:
        pos = array_fixture
        common_setup(pos,raid_type=raid_type, nr_data_drives=nr_data_drives)
        
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
@pytest.mark.parametrize("io_type", ["block", "xfs", "ext4"])
def test_wt_array_one_hour_FIO(
    array_fixture, raid_type, nr_data_drives, io_type
):
    logger.info(
        " ==================== Test : test_wt_array_xfs_file_FIO ================== "
    )
    try:
        mount_point = None
        pos = array_fixture

        common_setup(pos,raid_type=raid_type, nr_data_drives=nr_data_drives)
        
        # Run File IO and Block IO Parallely
        fio_cmd = f"fio --name=random_write --ioengine=libaio --rw=randwrite \
            --iodepth=64 --direct=1 --bs=128k --time_based --runtime=30 --size=1g"
        nvme_devs = pos.client.nvme_list_out

        if io_type == "block":
            io_mode = True  # Set True this to Block IO
        else:
            io_mode = False  # Set False this to File IO
            assert pos.client.create_File_system(nvme_devs, fs_format=io_type)
            out, mount_point = pos.client.mount_FS(nvme_devs)
            nvme_devs = mount_point
            assert out == True

        out, async_io = pos.client.fio_generic_runner(
            nvme_devs, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
        )
        assert out == True

        # Wait for async FIO completions
        while True:
            time.sleep(120)  # Wait for 2 minutes
            if not async_io.is_complete():
                logger.info("Sleep for 2 minutes. FIO is running...")
                continue
            break
        
        if mount_point:
            assert pos.client.unmount_FS(nvme_devs) == True
            mount_point = None
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_wt_array_block_IO(array_fixture, raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_block_IO ================== "
    )
    try:
        pos = array_fixture
        common_setup(pos,raid_type=raid_type, nr_data_drives=nr_data_drives)
        

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

