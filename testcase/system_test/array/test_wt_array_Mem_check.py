from common_libs import *
import pytest

import logger

logger = logger.get_logger(__name__)

array_list = [
    ("no-raid", 1, "Block"),
    ("RAID0", 2, "Block"),
    ("RAID10", 4, "Block"),
    ("RAID10", 2, "Block"),
    ("no-raid", 1, "File"),
    ("RAID0", 2, "File"),
    ("RAID10", 4, "File"),
    ("RAID10", 2, "File"),
]


@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives, IO", array_list)
def test_wt_array_Mem_check(
    array_fixture, raid_type, nr_data_drives, IO
):
    logger.info(
        " ==================== Test : test_wt_array_Mem_check ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
       
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
       
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True
        run_io(pos)
        
        if IO == "File":
            dev = [pos.client.nvme_list_out[0]]

            assert pos.client.create_File_system(dev, fs_format="xfs")
            status, mount_point = pos.client.mount_FS(dev)
            assert status == True

            fio_cmd = "fio --name=Rand_RW  --runtime=30 --ioengine=sync  --iodepth=32 --rw=write --size=1g bs=32kb --direct=1 --verify=md5"
            assert (
                pos.client.fio_generic_runner(
                    mount_point, fio_user_data=fio_cmd, IO_mode=False, run_async=True
                )[0]
                == True
            )
            assert status == True
            assert pos.client.unmount_FS(mount_point) == True
            assert pos.client.delete_FS(mount_point) == True

        else:

            assert (
                pos.client.fio_generic_runner(
                    pos.client.nvme_list_out,
                    fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=300",
                    run_async=True,
                )[0]
                == True
            )
        pos.client.check_system_memory()

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        if IO == "File":
            assert pos.client.unmount_FS(mount_point) == True
            assert pos.client.delete_FS(mount_point) == True
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0