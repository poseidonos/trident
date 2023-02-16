import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_raid6_array_disk_fail(array_fixture, array_mount):
    """
    The purpose of this test is to create a RAID6 array Mounted as WT or WB. 
    Create 16 volumes and run Block IO. Fail data disks in different rebuild interval.
    Verification: POS CLI, Fault Tolarance, End to End Data Flow
    """
    logger.info(
        f" ==================== Test : test_raid6_array_disk_fail[{array_mount}] ================== "
    )
    pos = array_fixture
    try:
        num_vols = 16
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < RAID6_MIN_DISKS + 4:
            pytest.skip("Less number of data disk")

        num_data_disk = RAID6_MIN_DISKS 
        num_spare_disk = len(pos.cli.system_disks) - RAID6_MIN_DISKS
        assert single_array_data_setup(pos.data_dict, "RAID6", num_data_disk,
                                    num_spare_disk, array_mount, False) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.subsystem_list()[0] == True
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

@pytest.mark.parametrize("write_mix_read", [80, 20, 50])
def test_raid6_array_disk_fail_random_io(array_fixture, write_mix_read):
    """
    The purpose of this test is to create two RAID6 arrays with 4 data and 2 spare drives Mounted as WT or WB.
    Create 16 volumes and run Block IO Mix of Random Write and Read IO. Fail data disks in different rebuild 
    interval.
    Verification: POS CLI, Fault Tolarance, End to End Data Flow
    """
    logger.info(
        f" ==================== Test : test_raid6_array_disk_fail_random_io[{write_mix_read}] ================== "
    )
    pos = array_fixture
    try:
        num_vols = 16
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", "RAID6"), 
                                      arrays_num_disks, (2, 2), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, num_vols,
                                                subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run FIO for 30 minutes
        fio_cmd = f"fio --name=rand_write --ioengine=libaio --rw=readwrite --iodepth=64 --bs=128k "\
                  f"--size=50gb --numjobs=4 --group_reporting --runtime=1800 --time_based --rwmixread={write_mix_read}"

        # Restart The IO
        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                    fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("Wait for 15 minutes before going to disk hot remove")
        time.sleep(900)

        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        disk_remove_interval_list = [(50, 100)]
        assert array_disks_hot_remove(pos, array_name, disk_remove_interval_list) == True

        # Wait for async fio to complete
        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=120) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.parametrize("raid_type", ["RAID5", "RAID10"])
def test_raid6_array_max_disk_fail(array_fixture, raid_type):
    """
    The purpose of this test is to create a RAID6 array with other raid types (RAID5, RAID10)
    Mounted as WT or WB. Create 16 volumes and run Block IO Mix of Random Write and Read IO.
    Fail the data disks upto the max fault tolarance, verify IO is working in degraded state.
    Verification: POS CLI, Fault Tolarance, End to End Data Flow
    """
    logger.info(
        f" ==================== Test : test_raid6_array_max_disk_fail[{raid_type}] ================== "
    )
    pos = array_fixture
    try:
        num_vols = 16
        num_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
        arrays_num_disks = (RAID6_MIN_DISKS, num_disk)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", raid_type), 
                                      arrays_num_disks, (0, 0), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, num_vols,
                                                subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run FIO for 30 minutes
        fio_cmd = f"fio --name=test_seqwrite --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                   "--size=200gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"

        # Restart The IO
        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                    fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("Wait for 5 minutes before going to disk hot remove")
        time.sleep(300)

        # Disk Fail on Both Array
        for pos_array in pos.data_dict["array"]["pos_array"]:
            array_name = pos_array["array_name"]
            raid_type = pos_array["raid_type"]
            num_disk_remove = RAID_MAX_DISK_FAIL_DICT[raid_type]

            if num_disk_remove > 1:
                disk_remove_interval_list = [(50, 50)]
            elif num_disk_remove == 1:
                disk_remove_interval_list = [(50, )]
            assert array_disks_hot_remove(pos, array_name, disk_remove_interval_list) == True

        # Wait for rebuild to complete in both array
        for pos_array in pos.data_dict["array"]["pos_array"]:
            array_name = pos_array["array_name"]
            assert pos.cli.array_info(array_name=array_name)[0] == True
            assert pos.cli.array_data[array_name]["situation"] == "DEGRADED"
            assert pos.cli.array_data[array_name]["state"] == "BUSY"

        # Wait for async fio to complete
        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=120) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_raid6_array_three_disk_fail_during_io(array_fixture):
    """
    The purpose of this test is to create two RAID6 arrays Mounted as WT or WB. Create 16 volumes and
    run Block IO Mix of Random Write and Read IO. Fail three data disks in different rebuild interval.
    Verification: POS CLI, Fault Tolarance, End to End Data Flow, No POS Crash
    """
    logger.info(
        f" ==================== Test : test_raid6_array_three_disk_fail_during_io ================== "
    )
    pos = array_fixture
    try:
        num_vols = 16
        arrays_num_disks = (RAID6_MIN_DISKS, RAID6_MIN_DISKS)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks) + 2:
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", "RAID6"), 
                                      arrays_num_disks, (1, 1), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert volume_create_and_mount_multiple(pos, num_vols,
                                                subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        async_io_list = []
        for pos_array in pos.data_dict["array"]["pos_array"]:
            array_name = pos_array["array_name"]

            assert pos.client.nvme_list(model_name=array_name) == True
            nvme_devs = pos.client.nvme_list_out

            # Run FIO for 30 minutes
            fio_cmd = "fio --name=rand_write --ioengine=libaio --rw=readwrite --iodepth=64 --bs=128k "\
                      "--size=50gb --numjobs=4 --group_reporting --runtime=1800 --time_based"

            # Restart The IO
            out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                        fio_user_data=fio_cmd, run_async=True)
            assert out == True

            async_io_list.append(async_io)

        # Fail three data Disks from Array 1
        logger.info("Wait for 5 minutes before going to disk hot remove")
        time.sleep(300)

        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]

        disk_remove_interval_list = [(50, 50, 50)]
        assert array_disks_hot_remove(pos, array_name, disk_remove_interval_list) == True

        # First ans Second Arrat states STOP, BUSY
        array_states = ("STOP", "NORMAL")
        array_situation = ("FAULT", "NORMAL")

        assert pos.cli.array_list()[0] == True
        for idx, array_name in enumerate(pos.cli.array_dict.keys()): 
            assert pos.cli.array_info(array_name=array_name)[0] == True
            assert pos.cli.array_data[array_name]["situation"] == array_situation[idx]
            assert pos.cli.array_data[array_name]["state"] == array_states[idx]


        # Wait for async fio to complete
        assert wait_sync_fio([], nvme_devs, None, async_io_list[1], sleep_time=120) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
