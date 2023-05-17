from common_libs import *
import pytest
import time
import random
import logger

logger = logger.get_logger(__name__)


def wt_wb_io(pos):
    fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                            --iodepth=64 --direct=1 --bs=128k --size=4g"
    nvme_devs = pos.client.nvme_list_out
    half = int(len(nvme_devs) / 2)
    file_io_devs = nvme_devs[0 : half - 1]
    block_io_devs = nvme_devs[half : len(nvme_devs) - 1]
    assert pos.client.create_File_system(file_io_devs, fs_format="xfs")
    out, mount_point = pos.client.mount_FS(file_io_devs)
    assert out == True
    io_mode = False  # Set False this to File IO
    out, async_file_io = pos.client.fio_generic_runner(
        mount_point, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
    )
    assert out == True

    io_mode = True  # Set False this to Block IO
    out, async_block_io = pos.client.fio_generic_runner(
        block_io_devs, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
    )
    assert out == True

    # Wait for async FIO completions
    while True:
        time.sleep(30)  # Wait for 30 seconds
        file_io = async_file_io.is_complete()
        block_io = async_block_io.is_complete()

        msg = []
        if not file_io:
            msg.append("File IO")
        if not block_io:
            msg.append("Block IO")

        if msg:
            logger.info(
                "'{}' is still running. Wait 30 seconds...".format(",".join(msg))
            )
            continue
        break


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("RAID0", 2), ("RAID10", 4), ("RAID10", 2), ("no-raid", 1), ("RAID10", 8)],
)
def test_wt_wb_multi_array_file_Block_IO(array_fixture, raid_type, nr_data_drives):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(
        " ==================== Test : test_wt_wb_multi_array_file_Block_IO ================== "
    )
    mount_point = None
    try:
        pos = array_fixture
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][0]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][1]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 0
        pos.data_dict["array"]["pos_array"][1]["spare_device"] = 0
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = 256

        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True
        run_io(pos)
        # Connect client
        wt_wb_io(pos)

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
