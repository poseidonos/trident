import random
import time
import traceback
import logger
import pytest
logger = logger.get_logger(__name__)

NORAID_MIN_DISKS = 1
RAID0_MIN_DISKS = 2
RAID5_MIN_DISKS = 3
RAID6_MIN_DISKS = 4
RAID10_MIN_DISKS = 2

MAX_VOL_SUPPORTED = 256

RAID_MIN_DISK_REQ_DICT = {
    "NORAID": NORAID_MIN_DISKS,
    "RAID0":  RAID0_MIN_DISKS,
    "RAID5":  RAID5_MIN_DISKS,
    "RAID6":  RAID6_MIN_DISKS,
    "RAID10": RAID10_MIN_DISKS,
}

ARRAY_ALL_RAID_LIST = ["NORAID", "RAID0", "RAID5", "RAID6", "RAID10"]

NORAID_MAX_DISK_FAIL = 0
RAID0_MAX_DISK_FAIL = 0
RAID5_MAX_DISK_FAIL = 1
RAID6_MAX_DISK_FAIL = 2
RAID10_MAX_DISK_FAIL = 1

RAID_MAX_DISK_FAIL_DICT = {
    "NORAID": NORAID_MAX_DISK_FAIL,
    "RAID0": RAID0_MAX_DISK_FAIL,
    "RAID5": RAID5_MAX_DISK_FAIL,
    "RAID6": RAID6_MAX_DISK_FAIL,
    "RAID10": RAID10_MAX_DISK_FAIL,
}

def multi_array_data_setup(data_dict: dict, num_array: int, raid_types: tuple, 
                           num_data_disks: tuple, num_spare_disk: tuple,
                           array_mount: tuple, auto_create: tuple):
    data_dict["array"]["num_array"] = num_array
    for index in range(data_dict["array"]["num_array"]):
        pos_array =  data_dict["array"]["pos_array"][index]
        pos_array["raid_type"] = raid_types[index]
        pos_array["data_device"] = num_data_disks[index]
        pos_array["spare_device"] = num_spare_disk[index]
        pos_array["auto_create"] = "true" if auto_create[index] else "false" 
        if array_mount == "NO":
            pos_array["mount"] = "false"
        else:
            pos_array["mount"] = "true"
            pos_array["write_back"] = "true" if array_mount == "WB" else "false"

    return True

def single_array_data_setup(data_dict: dict, raid_type: str, 
                            num_data_disk: int, num_spare_disk: int,
                            array_mount: str, auto_create: bool):
    return multi_array_data_setup(data_dict, 1, (raid_type, ), 
                                  (num_data_disk,), (num_spare_disk, ),
                                  (array_mount, ), (auto_create, ))

def array_unmount_and_delete(pos, unmount=True, delete=True, info_array=False):
    try:
        assert pos.cli.list_array()[0] == True
        for array_name in pos.cli.array_dict.keys():
            if info_array:
                assert pos.cli.info_array(array_name=array_name)[0] == True

            if unmount and pos.cli.array_dict[array_name].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array_name)[0] == True
            
            if delete:
                assert pos.cli.delete_array(array_name=array_name)[0] == True
    except Exception as e:
        logger.error(f"Failed to Unmount or Delete array due to {e}")
        return False
    return True


def volume_create_and_mount_multiple(pos: object, num_volumes: int, vol_utilize=100, 
                                     array_list=None, mount_vols=True, subs_list=[]):
    try:
        if not array_list:
            assert pos.cli.list_array()[0] == True
            array_list = list(pos.cli.array_dict.keys())

        if not subs_list:
            assert pos.cli.list_subsystem()[0] == True
            subs_list = pos.target_utils.ss_temp_list

        for array_name in array_list:
            assert pos.cli.info_array(array_name=array_name)[0] == True
            array_cap = int(pos.cli.array_info[array_name]["size"])
            vol_size = (array_cap * (vol_utilize // 100) // num_volumes)
            vol_size = f"{int(vol_size // (1024 * 1024))}mb"     # Size in mb

            exp_res = True
            if num_volumes > MAX_VOL_SUPPORTED or vol_utilize > 100:
                exp_res = False

            vol_name_pre = f"{array_name}_POS_Vol"
            assert pos.target_utils.create_volume_multiple(array_name, num_volumes,
                                vol_name=vol_name_pre, size=vol_size) == exp_res

            assert pos.cli.list_volume(array_name=array_name)[0] == True
            if mount_vols:
                ss_list = [ss for ss in subs_list if array_name in ss]
                assert pos.target_utils.mount_volume_multiple(array_name,
                                        pos.cli.vols, ss_list[0]) == True
    except Exception as e:
        logger.error(f"Create and Mount Volume Failed due to {e}")
        traceback.print_exc()
        return False
    return True

def volume_unmount_and_delete_multiple(pos, array_list=None):
    try:
        if not array_list:
            assert pos.cli.list_array()[0] == True
            array_list = list(pos.cli.array_dict.keys())
        for array_name in array_list:
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            for vol_name in pos.cli.vol_dict.keys():
                if pos.cli.vol_dict[vol_name]["status"].lower() == "mounted":
                    assert pos.cli.unmount_volume(vol_name,
                                        array_name=array_name)[0] == True
                assert pos.cli.delete_volume(vol_name,
                                        array_name=array_name)[0] == True
    except Exception as e:
        logger.error(f"Volume Unmount or Delete Failed due to {e}")
        return False
    return True
    
def volume_create_and_mount_random(pos, array_list=None, subsyste_list=None, arr_cap_vol_list=None):
    try:
        if not array_list:
            assert pos.cli.list_array()[0] == True
            array_list = list(pos.cli.array_dict.keys())

        if not subsyste_list:
            assert pos.cli.list_subsystem()[0] == True
            subsyste_list = pos.target_utils.ss_temp_list

        if not arr_cap_vol_list:
            arr_cap_vol_list = [(1, 100), (2, 100), (256, 100), 
                                (256, 105), (257, 100), (257, 105)]

        random.shuffle(arr_cap_vol_list)
        num_volumes, cap_utilize = arr_cap_vol_list[0]

        return volume_create_and_mount_multiple(pos, num_volumes, cap_utilize,
                array_list=array_list, mount_vols=True, subs_list=subsyste_list)
    except Exception as e:
        logger.error(f"Volume Unmount or Delete Failed due to {e}")
        return False

def get_file_block_devs(nvme_devs, fio_type):
    file_io_devs, block_io_devs = [], []
    if fio_type.lower() == "file":
        file_io_devs = nvme_devs
    elif fio_type.lower() == "mix":
        half = len(nvme_devs) // 2
        file_io_devs = nvme_devs[:half]
        block_io_devs = nvme_devs[half:]
    else:
        block_io_devs = nvme_devs
    return file_io_devs, block_io_devs

def wait_sync_fio(file_io_devs, block_io_devs, async_file_io, 
                  async_block_io, sleep_time=30):
    try:
        # Wait for async FIO completions
        while True:
            time.sleep(sleep_time)  # Wait for 30 seconds
            msg = []
            if file_io_devs and not async_file_io.is_complete():
                msg.append("File IO")

            if block_io_devs and not async_block_io.is_complete():
                msg.append("Block IO")

            if msg:
                logger.info(f"{','.join(msg)} is running. Wait {sleep_time} seconds...")
                continue
            return True
    except Exception as e:
        logger.error(f"Async FIO Wait Failed due to {e}")
        return False

def run_fio_all_volumes(pos, fio_cmd=None, fio_type="block", size='5g',
                        file_mount='xfs', nvme_devs=[], sleep_time=30):
    try:
        mount_point = []
        async_file_io, async_block_io = None, None
        if not nvme_devs:
            assert pos.client.nvme_list() == True
            nvme_devs = pos.client.nvme_list_out

        if not fio_cmd:
            fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                    --iodepth=64 --direct=1 --bs=128k --size={size}"
        
        file_io_devs, block_io_devs = get_file_block_devs(nvme_devs, fio_type)

        if file_io_devs:
            assert pos.client.create_File_system(file_io_devs, fs_format=file_mount)
            out, mount_point = pos.client.mount_FS(file_io_devs)
            assert out == True
            io_mode = False  # Set False this to File IO
            out, async_file_io = pos.client.fio_generic_runner(
                mount_point, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
            )
            assert out == True
        if block_io_devs:
            io_mode = True  # Set True this to Block IO
            out, async_block_io = pos.client.fio_generic_runner(
                block_io_devs, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
            )
            assert out == True

        assert wait_sync_fio(file_io_devs, block_io_devs, async_file_io,
                             async_block_io, sleep_time=sleep_time) == True
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
            mount_point = False
    except Exception as e:
        logger.error(f"Async FIO Failed due to {e}")
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
        return False
    return True

def array_disks_hot_remove(pos, array_name, disk_remove_interval_list):
    """
    disk_remove_interval_list = list of interval of subsequent disk failure
                                e.g: [(100), (50, 100)]
                                Fail 1 disk and wait for rebuild to complete.
                                Fail 2 disks and wait for rebuild to complete

    """
    try:
        assert pos.cli.info_array(array_name=array_name)[0] == True
        data_disk_list = pos.cli.array_info[array_name]["data_list"]
        remaining_spare_disk = len(pos.cli.array_info[array_name]["spare_list"])

        for disk_rebuild in disk_remove_interval_list:
            if len(disk_rebuild) > remaining_spare_disk:
                logger.info(f"Skipped - Required {len(disk_rebuild)} spare drives. "\
                             "Available {remaining_spare_disk} drives")
                continue

            random.shuffle(data_disk_list)
            hot_remove_disks = data_disk_list[: len(disk_rebuild)]
            for rebuild_complete in disk_rebuild:
                data_devs = [hot_remove_disks.pop(0)]
                assert pos.target_utils.device_hot_remove(data_devs) == True
                assert pos.target_utils.pci_rescan() == True

                # Wait for array rebuilding if rebuild_complete != 0
                if not rebuild_complete:
                    assert pos.target_utils.array_rebuild_wait(array_name=array_name, 
                                            rebuild_percent=rebuild_complete) == True
        return True
    except Exception as e:
        logger.error(f"Array data disk hot remove failed due to {e}")
        return False
    
def vol_connect_and_run_random_io(pos, subs_list, size='20g'):
    try:
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        logger.info(f"******** Start IO *****************")

        fio_cmd = f"fio --name=test_randwrite --ioengine=libaio --rw=randwrite --iodepth=64 --bs=128k --size={size}"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        logger.info(f"******** IO Completed ********************* ")
        return True
    except Exception as e:
        logger.error(f"Random Write failed due to {e}")
        return False

def pos_system_restore_stop(pos, array_info=True, array_unmount=True, array_delete=True,
                            vol_unmount=True, vol_delete=True, client_disconnect=False):
    try:
        if client_disconnect:
            assert pos.target_utils.helper.check_system_memory() == True
            if pos.client.ctrlr_list()[1] is not None:
                assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

        assert pos.cli.list_array()[0] == True
        for array_name in pos.cli.array_dict.keys():
            if array_info:
                assert pos.cli.info_array(array_name=array_name)[0] == True
            
            assert pos.cli.list_volume()[0] == True
            for vol_name in pos.cli.vols:
                if ((vol_unmount or vol_delete) and 
                        pos.cli.vol_dict[vol_name]["status"].lower() == "mounted"):
                    assert pos.cli.unmount_volume(vol_name, array_name=array_name)[0] == True

                if vol_delete:
                    assert pos.cli.delete_volume(vol_name, array_name=array_name)[0] == True

            if ((array_delete or array_unmount) and 
                        pos.cli.array_dict[array_name].lower() == "mounted"):
                assert pos.cli.unmount_array(array_name=array_name)[0] == True

            if array_delete:
                assert pos.cli.delete_array(array_name=array_name)[0] == True
        return True
    except Exception as e:
        logger.error(f"Failed to restore and stop pos system due to {e}")
        return False

def array_disk_remove_replace(pos, array_list, replace=False, verify_rebuild=False,
                              verify_disk=False, rebuild_wait=True, delay=2,
                              disk_index=0, random_disk=True):
    try:
        rebuild_array_list = []
        selected_disk_dict = {}
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            data_disk_list = pos.cli.array_info[array]["data_list"]
            spare_disk_list = pos.cli.array_info[array]["spare_list"]
            array_situation = pos.cli.array_info[array]["situation"]
            if random_disk:
                random.shuffle(data_disk_list)
            selected_disk = data_disk_list[disk_index]
            selected_disk_dict[array] = selected_disk
            if not replace:
                if len(spare_disk_list):
                    rebuild_array_list.append(array)
                assert pos.target_utils.device_hot_remove([selected_disk]) == True
                assert pos.target_utils.pci_rescan() == True
            else:
                exp_res = True
                if array_situation != "NORMAL" or len(spare_disk_list) == 0:
                    exp_res = False
                else:
                    rebuild_array_list.append(array)
                assert pos.cli.replace_drive_array(selected_disk, array)[0] == exp_res

        time.sleep(delay)

        if verify_rebuild:
            for array in rebuild_array_list:
                assert pos.target_utils.check_rebuild_status(array_name=array) == True

        if rebuild_wait:
            assert pos.target_utils.array_rebuild_wait_multiple(rebuild_array_list) == True

        if verify_disk:
            for array in rebuild_array_list:
                assert pos.cli.info_array(array_name=array)[0] == True
                data_disk_list = pos.cli.array_info[array]["data_list"]
                assert selected_disk_dict[array] not in data_disk_list

    except Exception as e:
        logger.error(f"Failed to array disk replace/remove due to {e}")
        traceback.print_exc()
        return False
    return True


def array_add_spare_disk(pos, array_list, spare_disks=None, verify=True):
    try:
        if not spare_disks:
            assert pos.cli.list_device()[0] == True
            spare_disks = pos.cli.system_disks
        
        assert len(array_list) <= len(spare_disks)

        for array in array_list:
            spare_disk = spare_disks.pop(0)
            assert pos.cli.addspare_array(spare_disk, array_name=array)[0] ==  True
            if verify:
                assert pos.cli.info_array(array_name=array)[0] == True
                spare_disk_list = pos.cli.array_info[array]["spare_list"]
                assert (spare_disk in spare_disk_list) == True
    except Exception as e:
        logger.info(f"Failed to array disk replace/remove due to {e}")
        return False
    return True


############################  Fixture #############################
################ TODO move fixtures to conftest.py ################

from pos import POS

@pytest.fixture(scope="module")
def setup_cleanup_module():
    logger.info("========= SETUP MODULE ========")
    pos = POS()
    data_dict = pos.data_dict
    data_dict['array']['phase'] = "false"
    data_dict['volume']['phase'] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    yield pos

    logger.info("========= CLEANUP MODULE ========")
    assert pos.exit_handler(expected=True) == True
    del pos


@pytest.fixture(scope="function")
def setup_cleanup_function(setup_cleanup_module):
    logger.info("========== SETUP TEST =========")
    pos = setup_cleanup_module
    data_dict = pos.data_dict
    if not pos.target_utils.helper.check_pos_exit():
        data_dict['system']['phase'] = "true"
        data_dict['subsystem']['phase'] = "true"
        data_dict['device']['phase'] = "true"
        data_dict['array']['phase'] = "false"
        data_dict['volume']['phase'] = "false"
        assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    data_dict['system']['phase'] = "false"
    data_dict['subsystem']['phase'] = "false"
    data_dict['device']['phase'] = "false"

    yield pos

    logger.info("========== CLEANUP AFTER TEST =========")

    assert pos_system_restore_stop(pos, client_disconnect=True) == True
    logger.info("==========================================")
