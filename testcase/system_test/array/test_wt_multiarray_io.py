import pytest

import time
import logger
from common_libs import *
logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("RAID0", 2), ("RAID5", 3), ("RAID10", 4), ("RAID10", 2), ("no-raid", 1)],
)

def test_wt_multi_array_file_IO(array_fixture,raid_type, nr_data_drives
):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(
        " ==================== Test : test_wt_multi_array_file_IO ================== "
    )
    mount_point = None
    try:
        pos = array_fixture
        common_setup(pos=pos,raid_type=raid_type, nr_data_drives= nr_data_drives)
        # Run IO
        pos.client.check_system_memory()
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                            --iodepth=64 --direct=1 --bs=128k --size=4g"

        file_io_devs = nvme_devs
        assert pos.client.create_File_system(file_io_devs, fs_format="xfs")
        out, mount_point = pos.client.mount_FS(file_io_devs)
        assert out == True
        io_mode = False  # Set False this to File IO
        out, async_file_io = pos.client.fio_generic_runner(
            mount_point, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
        )
        assert out == True

        # Wait for async FIO completions
        while True:
            time.sleep(30)  # Wait for 30 seconds
            file_io = async_file_io.is_complete()

            msg = []
            if not file_io:
                msg.append("File IO")

            if msg:
                logger.info(
                    "'{}' is still running. Wait 30 seconds...".format(",".join(msg))
                )
                continue
            break
        # assert pos.client.delete_FS(mount_point) == True
        # assert pos.client.unmount_FS(mount_point) == True
        pos.client.check_system_memory()
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
    finally:
        if mount_point is not None:
            assert pos.client.unmount_FS(mount_point) == True


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("no-raid", 1), ("RAID5", 3), ("RAID10", 4)]
)
def test_wt_multi_array_Block_IO(array_fixture, raid_type, nr_data_drives
):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(
        " ==================== Test : test_wt_multi_array_Block_IO ================== "
    )
    try:
        pos = array_fixture
        common_setup(pos=pos,raid_type=raid_type, nr_data_drives= nr_data_drives)
        pos.client.check_system_memory()
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
