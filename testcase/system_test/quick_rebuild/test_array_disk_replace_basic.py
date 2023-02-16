from time import sleep
import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)

test_quick_rebuild = {
    "t3" : ("RAID5",  "WT", False, 256), # RAID Type, Mount Type, Auto Create, Num Vols
    "t4" : ("RAID5",  "WT", False, 2)
}

@pytest.mark.parametrize("test_param", test_quick_rebuild)
def test_array_data_disk_replace(array_fixture, test_param):
    """
    The purpose of this test is to create a array of RAID5/RAID6/RAID10 with 
    minimum required data drive and 2 spare drive. Create volumes and Run IO.
    During IO pefrom data Disk Replacement and verify disk is replaced.
    Verification: POS CLI
    """
    logger.info(
        f" ==================== Test : test_array_data_disk_replace[{test_param}] ================== "
    )
    try:
        pos = array_fixture
        raid_type, mount_type, auto_create, num_vols = test_quick_rebuild[test_param]

        data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       data_disk, 2, mount_type, auto_create) == True

        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert volume_create_and_mount_multiple(pos, num_vols, 
            array_list=array_list, mount_vols=True, subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                  "--size=10gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        out, async_block_io = pos.client.fio_generic_runner(
                nvme_devs, fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("Async IO Started... Wait for 5 minutes")
        time.sleep(300)

        # Array disk replace
        assert array_disk_remove_replace(pos, array_list, replace=True, 
                                 verify_rebuild=True, verify_disk=True) == True

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

test_params = [("RAID10", "WB", 2), ("RAID5", "WB", 2),("RAID6", "WB", 2),("RAID5", "WB", 256),("RAID6", "WT", 2)]
@pytest.mark.parametrize("raid_type, mount_type, num_vols", test_params)
def test_array_vol_disk_replace_all_spare(array_fixture, raid_type, mount_type, num_vols):
    """
    The purpose of this test is to create a array of differnt RAIDs with minimum
    required data drive and 2 spare drive. Create volumes as specified and Run IO.
    During the IO pefrom Disk Replace
    SPARE DRIVES = 2 
    Verification: POS CLI
    """
    logger.info(
        f" ==================== Test : test_array_vol_disk_replace_all_spare[{raid_type}] ================== "
    )
    pos = array_fixture
    try:
        data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       data_disk, 2, mount_type, True) == True

        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        assert pos.cli.array_list()[0] == True
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
        #update 
        time.sleep(60)

        # Array disk replace
        assert array_disk_remove_replace(pos, array_list, replace=True) == True

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True
        
        
        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        #Array disk replace Again using up all spare drives
        assert array_disk_remove_replace(pos, array_list, replace=True) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


test_params = [("RAID10", "WB", True), ("RAID10", "WB", False),
               ("RAID6",  "WT", True), ("RAID5",  "WT", False)]

@pytest.mark.parametrize("raid_type, mount_type, auto", test_params)
def test_array_max_vol_disk_replace_during_qr(array_fixture, raid_type, mount_type, auto):
    """
    The purpose of this test is to create a array of differnt RAID10 with minimum
    required data drive and 3 spare drive. Create 256 volumes and Run IO.
    During the IO pefrom Disk Replace
    SPARE DRIVES = 3 
    Try performing Diskreplacement whie QR in Progress
    Verification: POS CLI
    """
    logger.info(
        f" ==================== Test : test_array_max_vol_disk_replace_during_qr[{raid_type}] ================== "
    )
    pos = array_fixture
    try:
        data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       data_disk, 3, mount_type, auto) == True

        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert volume_create_and_mount_multiple(pos, 256, 
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

        # Array disk replace 1 drive 
        assert array_disk_remove_replace(pos, array_list, replace=True) == True

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())
  
        #Retrying  Array disk replace while Quick Rebuild in Progress
        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            data_disk_list = pos.cli.array_data[array]["data_list"]
            random.shuffle(data_disk_list)
            
            # Quick Rebuild Will be started 
            assert pos.cli.array_replace_disk(data_disk_list[0], array)[0] == True

            assert pos.target_utils.check_rebuild_status(array_name=array) == True

            # Trying Data Disk Replacment during Quick Rebuild
            status = pos.cli.array_replace_disk(data_disk_list[1], array)
            assert status[0] == False
            event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for array replace disk due to {event_name}")
            
            # Waiting for completion of Rebuild 
            assert pos.target_utils.array_rebuild_wait(array_name=array) == True
        
    
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.parametrize("raid_type, mount_type, auto", [("RAID10", "WB", False)])
def test_array_max_vol_disk_replace_during_rebuild(array_fixture, raid_type, mount_type, auto):
    """
    The purpose of this test is to create a array of differnt RAID10 with minimum
    required data drive and 2 spare drive. Create 256 volumes and Run IO.
    During the IO pefrom Disk Replace during the Rebuild
    SPARE DRIVES = 2 
    Try performing Diskreplacement whie QR in Progress
    Verification: POS CLI
    """
    logger.info(
        f" ==================== Test : test_array_max_vol_disk_replace_during_rebuild[{raid_type}] ================== "
    )
    pos = array_fixture
    try:
        data_disk = RAID_MIN_DISK_REQ_DICT[raid_type]

        assert single_array_data_setup(pos.data_dict, raid_type, 
                                       data_disk, 2, mount_type, auto) == True

        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert volume_create_and_mount_multiple(pos, 256, 
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

        # Array disk Remove 1 drive 
        # assert array_disk_remove_replace(pos, array_list, replace=True) == True

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            data_disk_list = pos.cli.array_data[array]["data_list"]
            random.shuffle(data_disk_list)
            
            #  Array disk remove and Rebuild Will be started 
            assert pos.target_utils.device_hot_remove([data_disk_list[0]]) == True
            assert pos.target_utils.pci_rescan() == True
            assert pos.target_utils.check_rebuild_status(array_name=array) == True

        
            # Trying Data Disk Replacment during  Rebuild
            status = pos.cli.array_replace_disk(data_disk_list[1], array)
            assert status[0] == False
            event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for array replace disk due to {event_name}")
            
            # Waiting for completion of Rebuild 
            assert pos.target_utils.array_rebuild_wait(array_name=array) == True

        assert wait_sync_fio([], nvme_devs, None, async_block_io) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
