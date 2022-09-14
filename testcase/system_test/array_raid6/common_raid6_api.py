import random
import time
from unittest import expectedFailure
import logger
logger = logger.get_logger(__name__)

NORAID_MIN_DISKS = 1
RAID0_MIN_DISKS = 2
RAID5_MIN_DISKS = 3
RAID6_MIN_DISKS = 4
RAID10_MIN_DISKS = 2
MAX_VOL_SUPPORTED = 256

ARRAY_ALL_RAID_LIST = [("NORAID", NORAID_MIN_DISKS),
                       ("RAID0",  RAID0_MIN_DISKS),
                       ("RAID5", RAID5_MIN_DISKS),
                       ("RAID6", RAID6_MIN_DISKS),
                       ("RAID10", RAID10_MIN_DISKS)]

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

            array_cap = pos.cli.array_info[array_name]["size"]
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
            array_cap_volumes = [(1, 100), (2, 100), (256, 100), 
                                (256, 105), (257, 100), (257, 105)]
            random.shuffle(array_cap_volumes)
            num_volumes, cap_utilize = array_cap_volumes[0]

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
                  async_block_io, wait_time=30):
    try:
        # Wait for async FIO completions
        while True:
            time.sleep(wait_time)  # Wait for 30 seconds
            msg = []
            if file_io_devs and not async_file_io.is_complete():
                msg.append("File IO")

            if block_io_devs and not async_block_io.is_complete():
                msg.append("Block IO")

            if msg:
                logger.info(f"{','.join(msg)} is running. Wait {wait_time} seconds...")
                continue
            return True
    except Exception as e:
        logger.error(f"Async FIO Wait Failed due to {e}")
        return False

def run_fio_all_volumes(pos, fio_cmd=None, fio_type="block", 
                        file_io='xfs', nvme_devs=[], wait=30):
    try:
        mount_point = []
        async_file_io, async_block_io = None, None
        if not nvme_devs:
            assert pos.client.nvme_list() == True
            nvme_devs = pos.client.nvme_list_out

        if not fio_cmd:
            fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                    --iodepth=64 --direct=1 --bs=128k --size=1g"
        
        file_io_devs, block_io_devs = get_file_block_devs(nvme_devs, fio_type)

        if file_io_devs:
            assert pos.client.create_File_system(file_io_devs, fs_format=file_io)
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
                             async_block_io, wait_time=wait) == True
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
            mount_point = False
    except Exception as e:
        logger.error(f"Async FIO Failed due to {e}")
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
        return False
    return True