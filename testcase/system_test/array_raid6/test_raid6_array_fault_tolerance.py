import pytest

from common_raid6_api import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_raid6_array_disk_fail(setup_cleanup_array_function, array_mount):
    """
    The purpose of this test is to create a RAID6 array Mounted as WT or WB. 
    Create 16 volumes and run Block IO. Fail data disks in different rebuild interval.
    Verification: POS CLI, Fault Tolarance, End to End Data Flow
    """
    logger.info(
        f" ==================== Test : test_raid6_array_disk_fail[{array_mount}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        num_vols = 16
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < RAID6_MIN_DISKS + 4:
            pytest.skip("Less number of data disk")

        num_data_disk = RAID6_MIN_DISKS 
        num_spare_disk = len(pos.cli.system_disks) - RAID6_MIN_DISKS
        assert single_array_data_setup(pos.data_dict, "RAID6", num_data_disk,
                                    num_spare_disk, array_mount, False) == True
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert pos.cli.list_subsystem()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, num_vols,
                                                subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        fio_cmd = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                  "--size=200gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                    fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("Wait for 5 minutes before going to disk hot remove")
        time.sleep(300)

        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        disk_remove_interval_list = [(100, ), (0, 100), (20, 100), (50, 100), (80, 100)]
        assert array_disks_hot_remove(pos, array_name, disk_remove_interval_list) == True

        # Wait for async fio to complete
        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=120) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
