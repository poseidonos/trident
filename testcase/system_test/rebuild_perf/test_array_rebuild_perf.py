from time import sleep
import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)



set_rebuild_perf_tests = {
    # Rebuild Perf, Block Size, Queue Depth, Work load
    "t0" : {"impact" : "low",     "bs" : "4k",   "qd" : 128, "rw" : "randwrite"},
    "t1" : {"impact" : "medium",  "bs" : "4k",   "qd" : 128, "rw" : "randwrite"},
    "t2" : {"impact" : "high",    "bs" : "4k",   "qd" : 128, "rw" : "randwrite"},
    "t3" : {"impact" : "low",     "bs" : "4k",   "qd" : 128, "rw" : "randread"},
    "t4" : {"impact" : "medium",  "bs" : "4k",   "qd" : 128, "rw" : "randread"},
    "t5" : {"impact" : "high",    "bs" : "4k",   "qd" : 128, "rw" : "randread"},
    "t6" : {"impact" : "low",     "bs" : "128k", "qd" : 4,   "rw" : "write"},
    "t7" : {"impact" : "high",    "bs" : "4k",   "qd" : 128, "rw" : "read"},
    "t8" : {"impact" : "high",    "bs" : "128k", "qd" : 4,   "rw" : "write"},
    "t9" : {"impact" : "low",     "bs" : "128k", "qd" : 4,   "rw" : "read"},
    "t10" :{"impact" : "medium",  "bs" : "128k", "qd" : 4,   "rw" : "write"},
    "t11" :{"impact" : "high",    "bs" : "128k", "qd" : 4,   "rw" : "read"},
}

@pytest.mark.regression
@pytest.mark.rebuild_perf
@pytest.mark.parametrize("test_param", set_rebuild_perf_tests)
def test_set_rebuild_perf(array_fixture, test_param):
    """
    The purpose of this test is to create a RAID5 array. Create 2 volumes of 100 GB each. 
    Run IO of one of the type (randwrite, randread, write, read) in first volume. 
    During IO pefrom data Disk Hot Remove and verify disk is replaced. 
    Run IO on second volume. During IO set the rebuild perf impact value. 
    Verification: POS CLI
    """
    logger.info(
        f" ==================== Test : test_set_rebuild_perf[{test_param}] ================== "
    )
    try:
        pos = array_fixture
        raid_type, mount_type, auto_create = "RAID5", "WT", True
        rpi_dict = set_rebuild_perf_tests[test_param]
        qd, bs, rw = rpi_dict["qd"], rpi_dict["bs"], rpi_dict["rw"]
        num_vols = 2

        data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       data_disk, 2, mount_type, auto_create) == True

        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert volume_create_and_mount_multiple(pos, num_vols,  
            array_list=array_list, mount_vols=True, subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Fill total 100 GB data to both volumes.
        fio_cmd = "fio --size=200gb --ioengine=libaio --iodepth=128 --rw=randwrite --bs=128k --direct=1 --name=test_randwrite"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        fio_cmd = "fio --size=200gb --ioengine=libaio --iodepth={qd} --rw={rw} --bs={bs} --direct=1 --name=test_{rw}"

        out, async_block_io = pos.client.fio_generic_runner(
                nvme_devs, fio_user_data=fio_cmd, run_async=True)
        assert out == True

        # Array disk hot remove
        assert array_disk_remove_replace(pos, array_list, verify_rebuild=True, rebuild_wait=False) == True

        assert pos.cli.setposproperty_system(rpi_dict["impact"])[0] == True

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True

        fio_read  =  pos.client.fio_par_out["read"]
        fio_write =  pos.client.fio_par_out["write"]
        logger.info(f"FIO - Size : 100GB, IO Depth : {qd}, Block Size : {bs}, RW : {rw}")
        logger.info(f"Read  - BW : {fio_read['bw']}, IOPS : {fio_read['iops']}")
        logger.info(f"Write - BW : {fio_write['bw']}, IOPS : {fio_write['iops']}")

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
