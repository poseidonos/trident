from time import sleep
import pytest

from pos import POS
from common_test_api import *

import logger
logger = logger.get_logger(__name__)

remove_disk = ["spare_disk", "other_data_disk", "same_data_disk", "no_disk"]

@pytest.mark.parametrize("remove_disk", remove_disk)
def test_array_rebuild_data_integrity(setup_cleanup_array_function, remove_disk):
    """
    The purpose of this test is to create RAID5 array with 3 data drive and 1 spare drive. 
    Create and mount 2 multiple volumes to each array and utilize its full capacity.  
    Verification: POS CLI, End to End Data Flow, Data Integrity
    """
    logger.info(
        f" ==================== Test : test_array_rebuild_data_integrity[{remove_disk}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        raid_type = "RAID5"
        num_vols = 2
        num_data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
        num_spare_disk = 1
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < (num_data_disk + num_spare_disk):
            pytest.skip("Less number of system disks")

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       num_data_disk, num_spare_disk,
                                       "WT", False) == True

        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert volume_create_and_mount_multiple(pos, num_vols) == True
        subs_list = pos.target_utils.ss_temp_list

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                  "--size=50gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        out, async_block_io = pos.client.fio_generic_runner(
                nvme_devs, fio_user_data=fio_cmd, run_async=True)
        assert out == True

        time.sleep(120) # Wait for 2 minutes
        array_name = pos.data_dict['array']["pos_array"][0]["array_name"]
        assert pos.cli.array_info(array_name=array_name)[0] == True
        data_disk_list = pos.cli.array_data[array_name]["data_list"]
        spare_disk_list = pos.cli.array_data[array_name]["spare_list"]

        random.shuffle(data_disk_list)
        replace_disk = data_disk_list[0]
        assert pos.cli.array_replace_disk(replace_disk, array_name)[0] == True
        time.sleep(2)

        if remove_disk == "spare_disk":
            exp_array_situation = "degraded"
            selected_disk = spare_disk_list[0]
        elif remove_disk == "other_data_disk":
            exp_array_situation = "fault"
            selected_disk = data_disk_list[1]
        elif remove_disk == "same_data_disk":
            exp_array_situation = "rebuilding"
            selected_disk = data_disk_list[0]
        else:
            exp_array_situation = "rebuilding"
            selected_disk = []

        if selected_disk:
            assert pos.target_utils.device_hot_remove([selected_disk]) == True
            assert pos.target_utils.pci_rescan() == True
            
        time.sleep(2) # Wait 2 seconds and verify the rebuilding should not start
        assert pos.cli.array_info(array_name=array_name)[0] == True
        assert pos.cli.array_data[array_name]["situation"].lower() == exp_array_situation

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True

        fio_cmd = "fio --name=seq_read --ioengine=libaio --rw=read --iodepth=64 --bs=128k "\
                  "--size=20gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.parametrize("raid_type", ["RAID5", "RAID6", "RAID10"])
def test_disk_replace_degraded_array(setup_cleanup_array_function, raid_type):
    """
    The purpose of this test is to create two RAID5/RAID6 array with minimum required
    data drives. Create and mount 2 multiple volumes to each array and utilize its full
    capacity. Run IO and Hot remove the disk so it move it to degraded array.
    Do disk replace. Add a spare disk. Then do disk replace.

    Verification: Disk replace to degraded array
    """
    logger.info(
        f" ==================== Test : test_disk_replace_degraded_array[{raid_type}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        num_disks = RAID_MIN_DISK_REQ_DICT[raid_type]
        arrays_num_disks = (num_disks, num_disks)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < (2 * num_disks + 2):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, (raid_type, raid_type),
                    arrays_num_disks, (0, 0), ("WT", "WB"), (False, False)) == True
        
        pos.data_dict["volume"]["phase"] = "true"
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        subs_list = pos.target_utils.ss_temp_list

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                  "--size=100gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        out, async_block_io = pos.client.fio_generic_runner(
                nvme_devs, fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("Async IO Started... Wait for 5 minutes")
        time.sleep(300)

        array_name = pos.data_dict['array']["pos_array"][0]["array_name"]
        assert pos.cli.array_info(array_name=array_name)[0] == True
        data_disk_list = pos.cli.array_data[array_name]["data_list"]

        random.shuffle(data_disk_list)

        assert pos.target_utils.device_hot_remove([data_disk_list[0]]) == True
        assert pos.target_utils.pci_rescan() == True

        assert pos.cli.array_info(array_name=array_name)[0] == True
        array_situation = pos.cli.array_data[array_name]["situation"].lower()
        assert array_situation == "degraded"

        assert pos.cli.array_replace_disk(data_disk_list[0], array_name)[0] == False

        assert pos.cli.device_list()[0] == True
        spare_disk = pos.cli.system_disks[:2]
        assert pos.cli.array_addspare(spare_disk[0], array_name=array_name)[0] ==  True
        assert pos.cli.array_addspare(spare_disk[1], array_name=array_name)[0] ==  True
        time.sleep(2)

        assert pos.target_utils.array_rebuild_wait(array_name=array_name) == True

        assert pos.cli.array_info(array_name=array_name)[0] == True
        array_situation = pos.cli.array_data[array_name]["situation"].lower()
        assert array_situation == "normal"

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True

        fio_cmd = "fio --name=seq_read --ioengine=libaio --rw=read --iodepth=64 --bs=128k "\
                  "--size=20gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.parametrize("raid_type", ["RAID5", "RAID6", "RAID10"])
def test_spare_disk_fail_during_disk_replace(setup_cleanup_array_function, raid_type):
    """
    The purpose of this test is to create a RAID5/RAID6/RAID10 array with minimum required
    data drives and two spare drives. Create and mount multiple volumes to each array and 
    utilize its full capacity. Run IO and Do disk replace. Duing disk replace fail the spare 
    disk. Once rebuild is completed verify the data integrity.
    Verification: Disk replace to degraded array
    """
    logger.info(
        f" ==================== Test : test_spare_disk_fail_during_disk_replace[{raid_type}] ================== "
    )
    pos = setup_cleanup_array_function
    try:
        num_data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
        num_spare_disk = 2
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < (num_data_disk + num_spare_disk):
            pytest.skip("Less number of data disk")

        assert single_array_data_setup(pos.data_dict, raid_type, num_data_disk,
                                    num_spare_disk, "WT", False) == True
        
        pos.data_dict["volume"]["phase"] = "true"
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        subs_list = pos.target_utils.ss_temp_list

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                  "--size=100gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        out, async_block_io = pos.client.fio_generic_runner(
                nvme_devs, fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("Async IO Started... Wait for 5 minutes")
        time.sleep(300)

        array_name = pos.data_dict['array']["pos_array"][0]["array_name"]
        assert pos.target_utils.array_rebuild_wait(array_name=array_name) == True

        assert pos.cli.array_info(array_name=array_name)[0] == True
        spare_disk_list = pos.cli.array_data[array_name]["spare_list"]
        assert pos.target_utils.device_hot_remove([spare_disk_list[0]]) == True
        assert pos.target_utils.pci_rescan() == True

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True

        fio_cmd = "fio --name=seq_read --ioengine=libaio --rw=read --iodepth=64 --bs=128k "\
                  "--size=20gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


disk_replace_remove = ["replace", "remove"]
@pytest.mark.parametrize("disk_replace_remove", disk_replace_remove)
def test_array_raid6_disk_replace_remove(setup_cleanup_array_function, disk_replace_remove):
    """
    The purpose of this test is to create an array of RAID6 with minimum required 
    data drive and 2 spare drive. Create volumes and Run IO. During IO pefrom data
    Disk Replacement and verify disk is replaced. During the first rebuild do 2nd 
    data disk remove/replace.
    Verification: Data Integrity
    """
    logger.info(
        f" ==================== Test : test_array_data_disk_replace_remove[{disk_replace_remove}] ================== "
    )
    try:
        pos = setup_cleanup_array_function
        raid_type = "RAID6"
        num_vols = 16
        data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       data_disk, 2, "WT", False) == True

        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert pos.cli.subsystem_list()[0] == True
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

        fio_cmd = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                  "--size=100gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        out, async_block_io = pos.client.fio_generic_runner(
                nvme_devs, fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("Async IO Started... Wait for 5 minutes")
        time.sleep(300)

        # Array replace first data disk
        assert array_disk_remove_replace(pos, array_list, replace=True, 
                                 verify_rebuild=True, verify_disk=False, 
                                 rebuild_wait=False, random_disk=False,
                                 disk_index=0) == True

        replace = True if disk_replace_remove == "replace" else False
        assert array_disk_remove_replace(pos, array_list, replace=replace,
                                   verify_rebuild=True, verify_disk=True,
                                   rebuild_wait=True, random_disk=False,
                                   disk_index=1) == True

        if replace:
            assert pos.target_utils.array_rebuild_wait_multiple(array_list) == True

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True
 
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


