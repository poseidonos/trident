import random
import time
import logger
logger = logger.get_logger(__name__)

NORAID_MIN_DISKS = 1
RAID0_MIN_DISKS = 2
RAID5_MIN_DISKS = 3
RAID6_MIN_DISKS = 4
RAID10_MIN_DISKS = 2

MAX_VOL_SUPPORTED = 256

RAID_MIN_DISK_REQ_DICT = {
    "no-raid": NORAID_MIN_DISKS,
    "RAID0":  RAID0_MIN_DISKS,
    "RAID5":  RAID5_MIN_DISKS,
    "RAID6":  RAID6_MIN_DISKS,
    "RAID10": RAID10_MIN_DISKS,
}

ARRAY_ALL_RAID_LIST = ["no-raid", "RAID0", "RAID5", "RAID6", "RAID10"]

NORAID_MAX_DISK_FAIL = 0
RAID0_MAX_DISK_FAIL = 0
RAID5_MAX_DISK_FAIL = 1
RAID6_MAX_DISK_FAIL = 2
RAID10_MAX_DISK_FAIL = 1

RAID_MAX_DISK_FAIL_DICT = {
    "no-raid": NORAID_MAX_DISK_FAIL,
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
            pos_array["write_back"] = "true" if array_mount == "WT" else "false"

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
            vol_size = (array_cap * (vol_utilize / 100) / num_volumes)
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
                logger.info(f"{ss_list}")
                assert pos.target_utils.mount_volume_multiple(array_name,
                                        pos.cli.vols, ss_list[0]) == True
    except Exception as e:
        logger.error(f"Create and Mount Volume Failed due to {e}")
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
            io_mode = True  # Set False this to Block IO
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

def array_disks_hot_remove(pos, array_name, disk_remove_interval_list, delay=2):
    """
    disk_remove_interval_list = list of interval of subsequent disk failure
                                e.g: [(100), (50, 100)]
                                Fail 1 disk and wait for rebuild to complete.
                                Fail 2 disks and wait for rebuild to complete

    """
    try:
        logger.info("*********** HOT REMOVE REBUILD START **************")
        for disk_rebuild in disk_remove_interval_list:
            logger.info(f"REBUILD INTERVAL : {disk_rebuild} ")
            assert pos.cli.info_array(array_name=array_name)[0] == True
            data_disk_list = pos.cli.array_info[array_name]["data_list"]

            random.shuffle(data_disk_list)
            hot_remove_disks = data_disk_list[: len(disk_rebuild)]
            logger.info(f"Hot remove disks: {hot_remove_disks}")
            for rebuild_complete in disk_rebuild:
                data_devs = [hot_remove_disks.pop(0)]
                assert pos.target_utils.device_hot_remove(data_devs) == True
                assert pos.target_utils.pci_rescan() == True

                # Wait for array rebuilding if rebuild_complete != 0
                time.sleep(delay)
                logger.info(f"Rebuild Wait: {rebuild_complete}")
                if rebuild_complete > 0:
                    assert pos.target_utils.array_rebuild_wait(array_name=array_name, 
                                            rebuild_percent=rebuild_complete) == True
        logger.info("*********** HOT REMOVE REBUILD COMPLETED **************")
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
