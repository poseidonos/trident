import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)

array_list = [("RAID0", RAID0_MIN_DISKS), ("RAID5", RAID5_MIN_DISKS), ("RAID10", RAID10_MIN_DISKS)]

@pytest.mark.parametrize("num_vols", [8])
@pytest.mark.parametrize("raid_type, num_disk", array_list)
def test_raid6_multi_arrays_data_integrity(array_fixture, raid_type, num_disk, num_vols):
    """
    The purpose of this test is to create two arrays and atleast 1 should be RAID 6. 
    Create and mount 8 volumes to each array and utilize its full capacity. 
    Run File IO, Block IO and Mix of File and Block IO.
    Verification: POS CLI, End to End Data Flow, Data Integrity
    """
    logger.info(
        f" ==================== Test : test_raid6_multi_arrays_data_integrity[{raid_type}-{num_disk}-{num_vols}] ================== "
    )
    pos = array_fixture
    try:
        arrays_num_disks = (RAID6_MIN_DISKS, num_disk)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", raid_type), 
                                      arrays_num_disks, (0, 0), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.target_utils.get_subsystems_list() == True
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


# Num of Volumes, IO (Write, Rand Write, Read, Random Read))
io_profiler = [(32, ("write", "randwrite", "read", "randread"))]

@pytest.mark.parametrize("io_profiler", io_profiler)
def test_raid6_arrays_block_io_profile(array_fixture, io_profiler):
    """
    The purpose of this test is to create two arrays and atleast 1 should be RAID 6. 
    Create and mount 8 volumes to each array and utilize its full capacity. 
    Run File IO, Block IO and Mix of File and Block IO.
    Verification: POS CLI, End to End Data Flow, Data Integrity
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_block_io_load[{io_profiler}] ================== "
    )
    pos = array_fixture
    try:
        num_vols = io_profiler[0]
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", "RAID6"), 
                                      arrays_num_disks, (0, 0), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, num_vols,
                                                subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        for fio_rw in io_profiler[1]:
            logger.info(f"******** FIO Start : {fio_rw} *****************")
            fio_cmd = f"fio --name=test_{fio_rw} --ioengine=libaio --rw={fio_rw} --iodepth=64 --bs=128k --size=50gb"

            assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

            logger.info(f"******** FIO Completed ********************* ")

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
