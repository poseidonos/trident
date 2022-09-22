import pytest

import logger as logging
import time
import pprint
from array_test_common import *

logger = logging.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_wt_array_block_file_FIO(
    setup_cleanup_array_function, raid_type, nr_data_drives
):
    logger.info(
        " ==================== Test : test_wt_array_block_file_FIO ================== "
    )
    try:
        mount_point = None
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        assert wt_array_setup(pos, raid_type, nr_data_drives, 0) == True

        num_vols = 256
        array_size = int(pos.cli.array_info[array_name].get("size"))
        vol_size = (
            f"{int(array_size // (1024 * 1024) / num_vols)}mb"  # Volume Size in MB
        )
        io_size = f"{int((array_size * 0.9) // (1024 * 1024) / num_vols)}mb"  # FIO IO size in MB

        assert (
            pos.target_utils.create_volume_multiple(
                array_name, num_vols, "pos_vol", size=vol_size
            )
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

        for ss in ss_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )

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
        # assert pos.client.delete_FS(mount_point) == True
        assert pos.client.unmount_FS(mount_point) == True
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
    [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
@pytest.mark.parametrize("io_type", ["block", "xfs", "ext4"])
def test_wt_array_one_hour_FIO(
    setup_cleanup_array_function, raid_type, nr_data_drives, io_type
):
    logger.info(
        " ==================== Test : test_wt_array_xfs_file_FIO ================== "
    )
    try:
        mount_point = None
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        assert wt_array_setup(pos, raid_type, nr_data_drives, 0) == True

        assert pos.cli.info_array(array_name=array_name)[0] == True
        array_size = int(pos.cli.array_info[array_name].get("size"))
        vol_size = f"{int(array_size // (1024 * 1024))}mb"  # Volume Size in MB
        io_size = f"{int((array_size * 0.9) // (1024 * 1024))}mb"  # FIO IO size in MB

        assert (
            pos.target_utils.create_volume_multiple(
                array_name, 1, "pos_vol", size=vol_size
            )
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

        for ss in ss_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        fio_cmd = f"fio --name=random_write --ioengine=libaio --rw=randwrite \
            --iodepth=64 --direct=1 --bs=128k --time_based --runtime=3600 --size={io_size}"

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
        assert pos.client.fio_parser() == True

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
def test_wt_array_block_IO(setup_cleanup_array_function, raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_block_IO ================== "
    )
    try:
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        assert wt_array_setup(pos, raid_type, nr_data_drives, 0) == True

        assert (
            pos.target_utils.create_volume_multiple(
                array_name, 256, "pos_vol", size="2gb"
            )
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

        for ss in ss_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )

        assert pos.client.nvme_list() == True

        # Run Block IO for an Hour
        fio_out = pos.client.fio_genericrunner(
            pos.client.nvme_list_out,
            fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=3600",
        )
        assert fio_out[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_empty_1_1():
    logger.info("Empty Test 1 of Script 1")
