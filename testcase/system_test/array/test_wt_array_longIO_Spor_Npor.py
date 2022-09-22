import pytest
from common_libs import *

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives,por",
    [
        ("no-raid", 1, "Npor"),
        ("RAID0", 2, "Npor"),
        ("RAID10", 4, "Npor"),
        ("no-raid", 1, "Spor"),
        ("RAID0", 2, "Spor"),
        ("RAID10", 4, "Spor"),
        ("RAID10", 8, "Spor"),
        ("RAID10", 8, "Npor"),
    ],
)
def test_wb_wt_array_long_fileIO_Npor_Spor(
    array_fixture, raid_type, nr_data_drives, por
):

    logger.info(
        " ==================== Test : test_wb_wt_array_long_fileIO_Npor_Spor ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
        pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = 1
        pos.data_dict["volume"]["pos_volumes"][0]["size"] = "200gb"

        logger.info("configuring POS as per TC req")
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)

        dev = [pos.client.nvme_list_out[0]]

        assert pos.client.create_File_system(dev, fs_format="xfs")
        status, mount_point = pos.client.mount_FS(dev)
        assert status == True

        fio_cmd = "fio --name=Rand_RW  --runtime=100 --ramp_time=60  --ioengine=sync  --iodepth=32 --rw=write --size=50g --bs=32kb --direct=1 --verify=md5"

        status, io_pro = pos.client.fio_generic_runner(
            mount_point, fio_user_data=fio_cmd, IO_mode=False, run_async=True
        )
        assert status == True
        assert pos.client.unmount_FS(mount_point) == True
        assert pos.client.delete_FS(mount_point) == True

        if por == "Npor":
            assert pos.target_utils.Npor() == True
        else:
            assert pos.target_utils.Spor(uram_backup=True) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
