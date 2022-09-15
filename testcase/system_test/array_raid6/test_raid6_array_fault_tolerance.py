import pytest

from common_raid6_api import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_raid6_arrays_disk_fail(setup_cleanup_array_function, array_mount):
    """
    The purpose of this test is to create a RAID6 array Mounted as WT or WB. 
    Create 16 volumes and run Block IO. During IO fail the data disks [1 or 2 disks]. 
    Verification: POS CLI, Fault Tolarance, End to End Data Flow
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_disk_fail[{array_mount}] ================== "
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
                  "--size=20gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                    fio_user_data=fio_cmd, run_async=True)
        assert out == True

        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        assert pos.cli.info_array(array_name=array_name)[0] == True
        data_disk_list = pos.cli.array_info[array_name]["data_list"]
        spare_disk_list = pos.cli.array_info[array_name]["spare_list"]

        disk_rebuild_wait_list = [(100, 100), (50, 100)]

        for disk_rebuild in disk_rebuild_wait_list:
            for rebuild_complete in disk_rebuild:
                data_devs = [data_disk_list.pop(0)]
                assert pos.target_utils.device_hot_remove(data_devs) == True
                assert pos.target_utils.pci_rescan() == True

                # Wait for array rebuilding
                assert pos.target_utils.array_rebuild_wait(array_name=array_name, 
                                        rebuild_percent=rebuild_complete) == True
        # Wait for async fio to complete
        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=120) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)