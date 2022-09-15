import pytest

from common_raid6_api import *

import logger
logger = logger.get_logger(__name__)

array_list = [("RAID0", RAID0_MIN_DISKS), ("RAID5", RAID5_MIN_DISKS), ("RAID10", RAID5_MIN_DISKS)]

@pytest.mark.parametrize("num_vols", [8])
@pytest.mark.parametrize("raid_type, num_disk", array_list)
def test_raid6_multi_arrays_data_integrity(setup_cleanup_array_function, raid_type, num_disk, num_vols):
    """
    The purpose of this test is to create two arrays and atleast 1 should be RAID 6. 
    Create and mount 8 volumes to each array and utilize its full capacity. 
    Run File IO, Block IO and Mix of File and Block IO.
    Verification: POS CLI, End to End Data Flow, Data Integrity
    """
    logger.info(
        f" ==================== Test : test_raid6_multi_arrays_data_integrity[{ raid_type}-{num_disk}-{num_vols}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        arrays_num_disks = (RAID6_MIN_DISKS, num_disk)
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", raid_type), 
                                      arrays_num_disks, (0, 0), ("WT", "WB"),
                                      (False, False)) == True
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

        assert run_fio_all_volumes(pos, fio_cmd=fio_cmd, fio_type="Mix") == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)