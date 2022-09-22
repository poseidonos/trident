import pytest
import random
from common_libs import *
import logger

logger = logger.get_logger(__name__)

array1 = [
    ("NO-RAID", 1),
    ("RAID0", 2),
    ("RAID5", 3),
    ("RAID10", 2),
    ("RAID10", 4),
    ("RAID10", 8),
]
array2 = [
    ("NO-RAID", 1),
    ("RAID0", 2),
    ("RAID5", 3),
    ("RAID10", 2),
    ("RAID10", 4),
    ("RAID10", 8),
]


@pytest.mark.regression
@pytest.mark.parametrize("io_type", ["block", "file"])
@pytest.mark.parametrize("array2_raid, array2_num_disk", array2)
@pytest.mark.parametrize("array1_raid, array1_num_disk", array1)
def test_wt_multi_array_QOS_FIO(
    array_fixture, array1_raid, array1_num_disk, array2_raid, array2_num_disk, io_type
):
    """
    Test Multi-Array of same RAID types mounted in WT mode
    1. Create 256 volumes to utilize total capacity of array
    2. Set QOS Max IOPS and Max BW to 10
    3. Run Write Block IO and File IO and verify QOS throtteling
    """
    logger.info(
        " ==================== Test : test_wt_multi_array_QOS_FIO ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = array1_raid
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = array2_raid
        pos.data_dict["array"]["pos_array"][0]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][1]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][0]["data_device"] = array1_num_disk
        pos.data_dict["array"]["pos_array"][1]["data_device"] = array2_num_disk
        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 0
        pos.data_dict["array"]["pos_array"][1]["spare_device"] = 0
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = 256
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
        assert pos.client.nvme_list() == True

        fio_cmd = f"fio --name=write --ioengine=libaio --rw=write --iodepth=64 \
                    --bs=128k --time_based --runtime=5 --direct=1 --size=256"

        nr_dev = 8
        for i in range(256 // nr_dev):

            nvme_dev_list = pos.client.nvme_list_out[i * nr_dev : (i + 1) * nr_dev]

            if io_type == "file":
                assert pos.client.create_File_system(nvme_dev_list, fs_format="xfs")
                out, mount_point = pos.client.mount_FS(nvme_dev_list)
                assert out == True
                device_list = mount_point
                io_mode = False  # Set False this to File IO
            else:
                device_list = nvme_dev_list
                io_mode = True  # Set False this to Block IO

            assert (
                pos.client.fio_generic_runner(
                    device_list, IO_mode=io_mode, fio_user_data=fio_cmd
                )[0]
                == True
            )

            fio_write = pos.client.fio_par_out["write"]
            logger.info(f"FIO write out {fio_write}")

            if io_type == "file":
                assert pos.client.unmount_FS(mount_point) == True

            qos_data = {"max_iops": 10, "max_bw": 10}
            fio_out = {}

            fio_out["iops"] = fio_write["iops"]
            fio_out["bw"] = fio_write["bw"] / 1000  # Conver to MB

            assert pos.client.fio_verify_qos(qos_data, fio_out, nr_dev) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        if io_type == "file":
            assert pos.client.unmount_FS(mount_point) == True
        pos.exit_handler(expected=False)
