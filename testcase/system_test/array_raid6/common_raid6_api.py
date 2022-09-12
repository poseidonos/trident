import logger
logger = logger.get_logger(__name__)

RAID6_MIN_DISKS = 4
MAX_VOL_SUPPORTED = 256

def multi_array_data_setup(data_dict: dict, num_array: int, raid_types: tuple, 
                           num_data_disks: tuple, num_spare_disk: tuple,
                           array_mount: tuple, auto_create: tuple):
    data_dict["array"]["num_array"] = num_array
    for index in range(data_dict["array"]["num_array"]):
        pos_array =  data_dict["array"]["pos_array"][index]
        pos_array["raid_type"] = raid_types[index]
        pos_array["data_device"] = num_data_disks[index]
        pos_array["spare_device"] = num_spare_disk[index]
        pos_array["auto_create"] = auto_create[index]
        if array_mount == "NO":
            pos_array["mount"] = False
        else:
            pos_array["mount"] = True
            pos_array["write_back"] = True if array_mount == "WT" else False

    return True

def single_array_data_setup(data_dict: dict, raid_type: str, 
                            num_data_disk: int, num_spare_disk: int,
                            array_mount: str, auto_create: bool):
    return multi_array_data_setup(data_dict, 1, (raid_type, ), 
                                  (num_data_disk,), (num_spare_disk, ),
                                  (array_mount, ), (auto_create, ))

def volume_create_and_mount_multiple(pos: object, array_list: list, vol_utilize: int,
                                     num_volumes: int, mount_vols=True, sbus_list=[]):
    try:
        for array_name in array_list():
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_cap = pos.cli.array_info[array_name]["size"]
            vol_size = ((array_cap * vol_utilize) / 100) / num_volumes
            vol_size = f"{int(vol_size // (1024 * 1024))}mb"     # Size in mb

            if num_volumes > MAX_VOL_SUPPORTED or vol_utilize > 100:
                exp_res = False

            vol_name_pre = f"{array_name}_POS_Vol"
            assert pos.target_utils.create_volume_multiple(array_name, num_volumes,
                                vol_name=vol_name_pre, size=vol_size) == exp_res

            assert pos.cli.list_volume(array_name=array_name)[0] == True
            if mount_vols:
                ss_list = [ss for ss in sbus_list if array_name in ss]
                assert pos.target_utils.mount_volume_multiple(array_name,
                                        pos.cli.vols, ss_list[0]) == True
    except Exception as e:
        logger.error(f"Create and Mount Volume Failed due to {e}")
        return False
    return True