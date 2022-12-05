import random
import time
import logger
import traceback
import pytest

logger = logger.get_logger(__name__)


### Common Global Constants ###########

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


####common libs used in the Test scripts##########

def nvme_connect(pos):
    """method to do nvme connect and list"""
    assert pos.target_utils.get_subsystems_list() == True
    for ss in pos.target_utils.ss_temp_list:
        assert (
            pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
            == True
        )
    assert pos.client.nvme_list() == True
    return True, pos.client.nvme_list_out

def nvme_disconnect(pos):
    """ Method to do nvme disconnect """
    is_pos_running = False
    if pos.target_utils.helper.check_pos_exit() == False:
        is_pos_running = True

    pos.client.reset(is_pos_running)
    return True

def run_io(
    pos,
    fio_command="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=30",
):
    """method to do nvme connect, list and run block IO"""

    out = nvme_connect(pos)
    assert out[0] == True
    assert (
        pos.client.fio_generic_runner(
            out[1],
            fio_user_data=fio_command,
        )[0]
        == True
    )
    assert nvme_disconnect(pos) == True
    return True

def common_setup(pos,raid_type, nr_data_drives):
    
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
       
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
       
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True
        run_io(pos)

def multi_array_data_setup(data_dict: dict, num_array: int, raid_types: tuple, 
                           num_data_disks: tuple, num_spare_disk: tuple,
                           array_mount: tuple, auto_create: tuple):
    """
    Create a multi array setup. Update the data dict values.
    """
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
    """
    Create a single array setup.
    """
    return multi_array_data_setup(data_dict, 1, (raid_type, ), 
                                  (num_data_disk,), (num_spare_disk, ),
                                  (array_mount, ), (auto_create, ))

def create_hetero_array(pos, raid_type, data_disk_req, spare_disk_req=None, 
                        array_index=0, array_unmount=None, array_info=False):
    """
    Common api to create array using hetero size device.
    data_disk_req: Dictionay to select data disk of required size e.g - {'mix': 2, 'any': 1}
    spare_disk_req: Dictionay to select spare disk of required size e.g -  {'mix': 2, 'any': 1}
    array_unmount:  Control flag to mount array. 
                  None - Do not mount
                  WT/WB - Mount Write Through/ Write Back
    """
    try:
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True

        reqired_disk = sum(data_disk_req.values())
        if spare_disk_req: 
            reqired_disk += spare_disk_req.values()
        system_disk = len(pos.cli.system_disks)

        if system_disk < reqired_disk :
            logger.info("Requied disks : {reqired_disk}; Available disks {system_disk}")
            pytest.skip(f"Insufficient disk count!!!")

        data_dict = pos.data_dict
        array_name = data_dict["array"]["pos_array"][array_index]["array_name"]
        uram_name = data_dict["device"]["uram"][array_index]["uram_name"]

        if not pos.target_utils.get_hetero_device(data_disk_req, spare_device_config=spare_disk_req, device_list=False):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                    spare=spare_drives, raid_type=raid_type,
                                    array_name=array_name)[0] == True
        if array_unmount:
            write_back = False if array_unmount == "WT" else True
            assert pos.cli.array_unmount(array_name=array_name, write_back=write_back)[0] == True

        if array_info: 
            assert pos.cli.array_info(array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Failed to create hetero array due to {e}")
        return False

    return True


def array_unmount_and_delete(pos, unmount=True, delete=True, info_array=False):
    """
    Common cleanup function to unmount and delete arrays
    """
    try:
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            if array_info:
                assert pos.cli.array_info(array_name=array_name)[0] == True

            if unmount and pos.cli.array_dict[array_name].lower() == "mounted":
                assert pos.cli.array_unmount(array_name=array_name)[0] == True
            
            if delete:
                assert pos.cli.array_delete(array_name=array_name)[0] == True
    except Exception as e:
        logger.error(f"Failed to Unmount or Delete array due to {e}")
        return False
    return True


def volume_create_and_mount_multiple(pos: object, num_volumes: int, vol_utilize=100, 
                        vol_size=None, array_list=None, mount_vols=True, subs_list=[]):
    """
    Common function to create and mount volumes
    """
    try:
        if not array_list:
            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())

        if not subs_list:
            assert pos.target_utils.get_subsystems_list() == True
            subs_list = pos.target_utils.ss_temp_list

        for array_name in array_list:
            assert pos.cli.array_info(array_name=array_name)[0] == True

            array_cap = int(pos.cli.array_data[array_name]["size"])
            if not vol_size:
                vol_size = (array_cap * (vol_utilize / 100) / num_volumes)
                vol_size = f"{int(vol_size // (1024 * 1024))}mb"     # Size in mb

            exp_res = True
            if num_volumes > MAX_VOL_SUPPORTED or vol_utilize > 100:
                exp_res = False

            vol_name_pre = f"{array_name}_POS_Vol"
            assert pos.target_utils.create_volume_multiple(array_name, num_volumes,
                                vol_name=vol_name_pre, size=vol_size) == exp_res

            assert pos.cli.volume_list(array_name=array_name)[0] == True
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
    """
    Common function to unmount and delete volumes. 
    """
    try:
        if not array_list:
            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())
        for array_name in array_list:
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name in pos.cli.vol_dict.keys():
                if pos.cli.vol_dict[vol_name]["status"].lower() == "mounted":
                    assert pos.cli.volume_unmount(vol_name,
                                        array_name=array_name)[0] == True
                assert pos.cli.volume_delete(vol_name,
                                        array_name=array_name)[0] == True
    except Exception as e:
        logger.error(f"Volume Unmount or Delete Failed due to {e}")
        return False
    return True
    
def volume_create_and_mount_random(pos, array_list=None, subsyste_list=None, arr_cap_vol_list=None):
    """
    Common function to create and mount random number of volumes
    """
    try:
        if not array_list:
            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())

        if not subsyste_list:
            assert pos.target_utils.get_subsystems_list() == True
            subsyste_list = pos.target_utils.ss_temp_list

        if not arr_cap_vol_list:
            arr_cap_vol_list = [(1, 100), (2, 100), (256, 100)]
        random.shuffle(arr_cap_vol_list)
        num_volumes, cap_utilize = arr_cap_vol_list[0]

        return volume_create_and_mount_multiple(pos, num_volumes, cap_utilize,
                array_list=array_list, mount_vols=True, subs_list=subsyste_list)
    except Exception as e:
        logger.error(f"Volume Unmount or Delete Failed due to {e}")
        return False



def get_file_block_devs(nvme_devs, fio_type):
    """
    Function to split use of nvme device as file or block IO
    """
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
    """
    Function to wait for async IO
    """
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
    """
    Common function to run FIO all nvme device.
    """
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
            logger.info(f"File IO Dev: {file_io_devs}")
            assert pos.client.create_File_system(file_io_devs, fs_format=file_mount)
            out, mount_point = pos.client.mount_FS(file_io_devs)
            assert out == True
            io_mode = False  # Set False this to File IO
            out, async_file_io = pos.client.fio_generic_runner(
                mount_point, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
            )
            assert out == True
        if block_io_devs:
            logger.info(f"Block IO Dev: {block_io_devs}")
            io_mode = True  # Set False this to Block IO
            out, async_block_io = pos.client.fio_generic_runner(
                block_io_devs, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
            )
            assert out == True

        assert wait_sync_fio(file_io_devs, block_io_devs, async_file_io,
                             async_block_io, sleep_time=sleep_time) == True
        if mount_point:
            logger.info(f"mount_point: {mount_point}")
            assert pos.client.unmount_FS(mount_point) == True
            mount_point = []
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
            assert pos.cli.array_info(array_name=array_name)[0] == True
            data_disk_list = pos.cli.array_data[array_name]["data_list"]

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
    
def vol_connect_and_run_random_io(pos, subs_list, size='20g', time_based=False, run_time='2m'):
    """
    Common function to connect to volumes are run random IO
    """
    try:
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        logger.info(f"******** Start IO *****************")

        fio_cmd = "fio --name=test_randwrite --ioengine=libaio --rw=randwrite --iodepth=64 --bs=128k"
        if time_based:
            fio_cmd += f" --time_based=1 --runtime={run_time}" 
        else:
            fio_cmd += f" --size={size}"

        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        logger.info(f"******** IO Completed ********************* ")
        return True
    except Exception as e:
        logger.error(f"Random Write failed due to {e}")
        return False

def pos_system_restore_stop(pos, array_info=True, array_unmount=True, array_delete=True,
                            vol_unmount=True, vol_delete=True, client_disconnect=False):
    """
    Common cleanup function to stop POS
    """
    try:
        if client_disconnect:
            assert pos.target_utils.helper.check_system_memory() == True
            if pos.client.ctrlr_list()[1] is not None:
                assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            if array_info:
                assert pos.cli.array_info(array_name=array_name)[0] == True
            
            assert pos.cli.volume_list()[0] == True
            for vol_name in pos.cli.vols:
                if ((vol_unmount or vol_delete) and 
                        pos.cli.vol_dict[vol_name]["status"].lower() == "mounted"):
                    assert pos.cli.volume_unmount(vol_name, array_name=array_name)[0] == True

                if vol_delete:
                    assert pos.cli.volume_delete(vol_name, array_name=array_name)[0] == True

            if ((array_delete or array_unmount) and 
                        pos.cli.array_dict[array_name].lower() == "mounted"):
                assert pos.cli.array_unmount(array_name=array_name)[0] == True

            if array_delete:
                assert pos.cli.array_delete(array_name=array_name)[0] == True
        return True
    except Exception as e:
        logger.error(f"Failed to restore and stop pos system due to {e}")
        return False


def array_disk_remove_replace(pos, array_list, replace=False, verify_rebuild=False,
                              verify_disk=False, rebuild_wait=True, delay=2,
                              disk_index=0, random_disk=True):
    """
    Common function to disk remove and replace.
    """
    try:
        rebuild_array_list = []
        selected_disk_dict = {}
        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            data_disk_list = pos.cli.array_data[array]["data_list"]
            spare_disk_list = pos.cli.array_data[array]["spare_list"]
            array_situation = pos.cli.array_data[array]["situation"]
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
                assert pos.cli.array_replace_disk(selected_disk, array)[0] == exp_res

        time.sleep(delay)

        if verify_rebuild:
            for array in rebuild_array_list:
                assert pos.target_utils.check_rebuild_status(array_name=array) == True

        if rebuild_wait:
            assert pos.target_utils.array_rebuild_wait_multiple(rebuild_array_list) == True

        if verify_disk:
            for array in rebuild_array_list:
                assert pos.cli.array_info(array_name=array)[0] == True
                data_disk_list = pos.cli.array_data[array]["data_list"]
                assert selected_disk_dict[array] not in data_disk_list

    except Exception as e:
        logger.error(f"Failed to array disk replace/remove due to {e}")
        traceback.print_exc()
        return False
    return True


def array_add_spare_disk(pos, array_list, spare_disks=None, verify=True):
    """
    Common function to add spare disks.
    """
    try:
        if not spare_disks:
            assert pos.cli.device_list()[0] == True
            spare_disks = pos.cli.system_disks
        
        assert len(array_list) <= len(spare_disks)

        for array in array_list:
            spare_disk = spare_disks.pop(0)
            assert pos.cli.array_addspare(spare_disk, array_name=array)[0] ==  True
            if verify:
                assert pos.cli.array_info(array_name=array)[0] == True
                spare_disk_list = pos.cli.array_data[array]["spare_list"]
                assert (spare_disk in spare_disk_list) == True
    except Exception as e:
        logger.info(f"Failed to array disk replace/remove due to {e}")
        return False
    return True
