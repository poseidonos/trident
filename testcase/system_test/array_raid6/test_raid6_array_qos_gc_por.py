import pytest

from pos import POS
from common_raid6_api import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.parametrize("raid_type", ARRAY_ALL_RAID_LIST)
def test_raid6_arrays_qos(setup_cleanup_array_function, raid_type):
    """
    The purpose of this test is to create two arrays and atleast 1 should be RAID 6. 
    Create and mount 2 volumes and utilize its capacity. Set QOS values to volumes.
    Verification: Block IO QOS throtelling
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_qos[{raid_type}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        num_vols = 2
        num_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
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

        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert volume_create_and_mount_multiple(pos, num_vols, 
                            array_list=array_list, subs_list=subs_list) == True

        maxiops, maxbw = 10, 10
        for array in array_list:
            assert pos.cli.list_volume(array_name=array)[0] == True
            for volname in pos.cli.vols:
                assert pos.cli.create_volume_policy_qos(arrayname=array, 
                    volumename=volname, maxiops=maxiops, maxbw=maxbw)[0] == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = "fio --name=test_seq_write --ioengine=libaio --iodepth=32 --rw=write --size=10g --bs=32k --direct=1"

        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        fio_out = {}
        fio_out["iops"] = pos.client.fio_par_out["write"]["iops"]
        fio_out["bw"] = pos.client.fio_par_out["write"]["bw"] / 1000  # Conver to MB

        # Verify the QOS Throttling
        assert pos.client.fio_verify_qos({"max_iops":maxiops, "max_bw":maxbw},
                                         fio_out,
                                         len(nvme_devs)) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.parametrize("por_operation", ["SPOR", "NPOR", "POR_LOOP"])
def test_raid6_arrays_por(setup_cleanup_array_function, por_operation):
    """
    The purpose of this test is to create two RAID6 arrays. Create and mount 2 volumes
    and utilize its full capacity. Run Block IO with known data pattern. Do SPOR-NPOR.
    Read and verify the data pattern.
    Verification: Data integrity after SPOR or  NPOR
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_por[{por_operation}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        num_vols = 2
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", "RAID6"),
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

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        pattern = "0x5678"

        fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                f"--size=200gb --do_verify=1 --verify=pattern --verify_pattern={pattern}"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        if por_operation == "POR_LOOP":
            por_list = ["NPOR", "SPOR", "NPOR", "SPOR", "NPOR"]
        else:
            por_list = [por_operation]

        for por in por_list:

            if por == "NPOR":
                assert pos.target_utils.Npor() == True

            else:
                assert pos.target_utils.Spor() == True

            fio_cmd = "fio --name=seq_read --ioengine=libaio --rw=read --iodepth=64 --bs=128k "\
                    f"--size=200gb --do_verify=1 --verify=pattern --verify_pattern={pattern}"
            assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.parametrize("gc_operation", ["normal", "wbt"])
def test_raid6_arrays_gc(setup_cleanup_array_function, gc_operation):
    """
    The purpose of this test is to create two rAID6 arrays. Mounted in WT and WB mode.
    Create and mount 2 volumes and utilize its capacity. Run Random Block IO (30, 70).
    Either write 80% or use WBT GC to trigger the gc during IO.
    Verification: POS GC and Data Integrity
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_gc[{gc_operation}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        num_vols = 2
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        assert pos.cli.list_device()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", "RAID6"),
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

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        if gc_operation == "normal":
            fio_cmd = "fio --name=rand_write --ioengine=libaio --numjobs=4 --rw=randwrite --iodepth=64 --bs=128k --size=85%"
            assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True
        else:
            fio_cmd = "fio --name=seq_write --ioengine=libaio --numjobs=4 --rw=write --iodepth=64 --bs=128k --size=15%"
            assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True
            assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True
            assert pos.cli.wbt_do_gc()[0] == True

        assert pos.cli.wbt_get_gc_status()[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

