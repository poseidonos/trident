import pytest
import time
import random
from common_libs import *

import logger
logger = logger.get_logger(__name__)
fio_cmd = "fio --name=Rand_RW  --runtime=43000 --ramp_time=60  --ioengine=sync  --iodepth=32 --rw=write --size=50g --bs=32kb --direct=1 --verify=md5"


def array_ops(pos):
    assert pos.cli.array_list()[0] == True
    array_name = list(pos.cli.array_dict.keys())[0]

    assert pos.cli.volume_list(array_name=array_name)[0] == True
    for volume in pos.cli.vols:
        pos.cli.volume_unmount(volumename=volume, array_name=array_name)
        pos.cli.volume_delete(volumename=volume, array_name=array_name)
    assert pos.cli.array_info(array_name=array_name)[0] == True
    assert pos.cli.array_unmount(array_name=array_name)[0] == True
    assert pos.cli.array_delete(array_name=array_name)[0] == True


def file_io(pos):

    dev = [pos.client.nvme_list_out[0]]

    assert pos.client.create_File_system(dev, fs_format="xfs")
    status, mount_point = pos.client.mount_FS(dev)
    assert status == True

    status, io_pro = pos.client.fio_generic_runner(
        mount_point, fio_user_data=fio_cmd, IO_mode=False, run_async=True
    )
    assert status == True
    # Wait for File IO completions
    while True:
        time.sleep(60)  # Wait for 1 minute
        file_io = io_pro.is_complete()

        msg = []
        if not file_io:
            msg.append("File IO")

        if msg:
            logger.info(
                "'{}' is still running. Wait  1 minute...".format(",".join(msg))
            )
            continue
        break

    assert pos.client.unmount_FS(mount_point) == True
    assert pos.client.delete_FS(mount_point) == True


def common_setup(pos, raid_type, nr_data_drives):
    pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
    pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
    pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
    pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
    pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
    pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = 1
    pos.data_dict["volume"]["pos_volumes"][0]["size"] = "200gb"
    pos.data_dict["volume"]["pos_volumes"][1]["size"] = "200gb"
    logger.info("configuring POS")
    assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
    assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True
    run_io(pos)
    file_io(pos)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("no-raid", 1), ("RAID0", 2), ("RAID10", 4)]
)
def test_wt_array_long_fileIO(array_fixture, raid_type, nr_data_drives):

    logger.info(
        " ==================== Test : test_wt_array_long_fileIO ================== "
    )
    try:
        pos = array_fixture
        common_setup(pos, raid_type, nr_data_drives)

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("no-raid", 1), ("RAID0", 2), ("RAID10", 4)]
)
def test_wt_wb_array_long_fileIO(array_fixture, raid_type, nr_data_drives):

    logger.info(
        " ==================== Test : test_wt_wb_array_long_fileIO ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 1
        common_setup(pos, raid_type, nr_data_drives)
        # unmount and delete array and volume
        array_ops(pos)

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("no-raid", 1), ("RAID0", 2), ("RAID10", 4)]
)
def test_wb_wt_array_long_fileIO(array_fixture, raid_type, nr_data_drives):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(
        " ==================== Test : test_wb_wt_array_long_fileIO ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 1
        pos.data_dict["array"]["pos_array"][0]["write_back"] = random.choice(
            [True, False]
        )
        common_setup(pos, raid_type, nr_data_drives)
        # unmount and delete array and volume
        array_ops(pos)

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
