import pytest
from array_test_common import *
import logger

logger = logger.get_logger(__name__)


array1 = [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 4)]
array2 = [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 4)]


@pytest.mark.regression
@pytest.mark.parametrize("array2", array2)
@pytest.mark.parametrize("array1", array1)
def test_wt_multi_array_FIO_SPOR_NPOR(setup_cleanup_array_function, array1, array2):
    """
    Test Multi-Array in all RAID combination with WT/WB mount.
    1. Run Write Block IO for an hour.
    2. Trigger SPOR
    3. Trigger NPOR
    """
    logger.info(
        " ==================== Test : test_wt_multi_array_FIO_SPOR_NPOR ================== "
    )
    try:
        pos = setup_cleanup_array_function
        array_name1 = "array1"
        array_name2 = "array2"

        array_raid_disk = (array1, array2)
        writeback = [False, True]

        array_list = []
        for id, array_name in enumerate((array_name1, array_name2)):
            array_list.append(
                {
                    "array_name": array_name,
                    "buffer_dev": f"uram{id}",
                    "raid_type": array_raid_disk[id][0],
                    "nr_data_drives": array_raid_disk[id][1],
                    "write_back": writeback[id],
                }
            )

        assert wt_test_multi_array_setup(array_list) == True

        for id, array_name in enumerate((array_name1, array_name2)):
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_data[array_name].get("size"))
            vol_size = f"{array_size // (1024 * 1024)}mb"  # Volume Size in MB

            assert (
                pos.target_utils.create_volume_multiple(
                    array_name, 1, "pos_vol", size=vol_size
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            ss_temp_list = pos.target_utils.ss_temp_list
            ss_list = [ss for ss in ss_temp_list if f"subsystem{id + 1}" in ss]
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

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        fio_cmd = f"fio --name=random_write --ioengine=libaio --rw=randwrite \
            --iodepth=64 --direct=1 --bs=128k --time_based --runtime=3600"

        assert (
            pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True
        )

        # Perfrom SPOR
        assert pos.target_utils.Spor() == True

        # Perform NPOR
        assert pos.target_utils.Npor() == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
