import pytest

from array_test_common import *

import logger
logger = logger.get_logger(__name__)
array = [("NORAID", 1), ("RAID0", 2)]


@pytest.mark.regression
@pytest.mark.parametrize("array_raid, array_num_disk", array)
def test_wt_multi_array_disabled_journal(
    array_fixture, array_raid, array_num_disk
):
    """
    Test Multi-Array in combination with WT/WB mount when journal is disable
    1. Run Write Block IO for an hour.
    """
    logger.info(
        " ==================== Test : test_wt_multi_array_disabled_journal ================== "
    )
    try:
        pos = array_fixture
        array_name1, array_name2 = "array1", "array2"

        array_writeback_list = (False, True)

        array_list = []
        for id, array_name in enumerate((array_name1, array_name2)):
            array_list.append(
                {
                    "array_name": array_name,
                    "buffer_dev": f"uram{id}",
                    "raid_type": array_raid,
                    "nr_data_drives": array_num_disk,
                    "write_back": array_writeback_list[id],
                }
            )

        assert wt_test_multi_array_setup(array_list) == True

        for id, array_name in enumerate((array_name1, array_name2)):
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_data[array_name].get("size"))
            vol_size = f"{array_size // (1024 * 1024)}mb"  # Volume Size in MB
            io_size = f"{array_size * 95 // (1024 * 1024 * 100)}mb"  # IO size is 95% of Vol size.

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

        # Run File IO for 12 hours
        fio_cmd = f"fio --name=write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --bs=128k --time_based --runtime=7200 --size={io_size}"

        assert pos.client.create_File_system(nvme_devs, fs_format="xfs")
        out, mount_point = pos.client.mount_FS(nvme_devs)
        assert out == True
        io_mode = False  # Set False this to File IO
        out, fio_out = pos.client.fio_generic_runner(
            mount_point, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=False
        )
        assert out == True

        logger.info(f"FIO out: {fio_out}")

        assert pos.client.unmount_FS(mount_point) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.client.unmount_FS(mount_point)
        pos.exit_handler(expected=False)
