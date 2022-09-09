import pytest

from array_test_common import *
import time

import logger
logger = logger.get_logger(__name__)


fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                            --iodepth=64 --direct=1 --bs=128k --size=100%"

@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives", [("RAID0", 2)])
def test_wt_array_io_spor(array_setup_cleanup, raid_type, nr_data_drives):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(
        " ==================== Test : test_wt_array_io_spor ================== "
    )
    try:
        pos = array_setup_cleanup
        assert wt_array_setup(pos, raid_type, nr_data_drives, 0) == True
        array_name = pos.data_dict['array']['pos_array'][0]["array_name"]

        assert pos.target_utils.get_subsystems_list() == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]

        assert (
            pos.cli.create_volume("pos_vol1", array_name=array_name, size="2000gb")[0]
            == True
        )
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

        # Connect client
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True

        # Run IO
        pos.client.check_system_memory()
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        block_io_devs = nvme_devs
        io_mode = True  # Set False this to Block IO
        out, async_block_io = pos.client.fio_generic_runner(
            block_io_devs, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
        )
        assert out == True

        # Wait for async FIO completions
        while True:
            time.sleep(30)  # Wait for 30 seconds
            block_io = async_block_io.is_complete()

            msg = []
            if not block_io:
                msg.append("Block IO")

            if msg:
                logger.info(
                    "'{}' is still running. Wait 30 seconds...".format(",".join(msg))
                )
                continue
            break

        # Perfrom SPOR
        assert pos.target_utils.Spor(uram_backup=False) == True

        pos.client.check_system_memory()
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_spor_wt_wb(array_setup_cleanup):
    try:
        pos = array_setup_cleanup
        pos.data_dict['volume']['phase'] = "true"
        assert pos.target_utils.pos_bring_up() == True
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out, fio_user_data=fio_cmd )[0] == True
        assert pos.target_utils.Spor(write_through=True) == True
    except Exception as e:
        pos.exit_handler()
        assert 0


@pytest.mark.regression
def test_npor_wt_wb(array_setup_cleanup):
    try:
        pos = array_setup_cleanup
        pos.data_dict['volume']['phase'] = "true"
        assert pos.target_utils.pos_bring_up() == True
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out, fio_user_data=fio_cmd )[0] == True
        assert pos.target_utils.Npor(write_through=True) == True
    except Exception as e:
        pos.exit_handler()
        assert 0