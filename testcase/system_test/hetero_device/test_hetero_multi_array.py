import pytest
import traceback
from common_libs import *

import logger
logger = logger.get_logger(__name__)

array = [("RAID5", 3),]

@pytest.mark.regression
@pytest.mark.parametrize("repeat_ops", [1, 100])
@pytest.mark.parametrize("array1_raid, array1_devs", array)
@pytest.mark.parametrize("array2_raid, array2_devs", array)
def test_hetero_multi_array(array_fixture, array1_raid, array1_devs, array2_raid, array2_devs, repeat_ops):
    """
    Test auto create arrays of no-raid with different NUMA node
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array ================== "
    )
    try:
        pos = array_fixture
        # Loop 2 times to create two RAID array of RAID5 using hetero device
        raid_types = (array1_raid, array2_raid)
        num_devs = (array1_devs, array2_devs)

        for i in range(repeat_ops):
            assert array_create_and_list(pos, raid_list=raid_types,
                                         num_devs=num_devs) == True
            for array_name in pos.cli.array_dict.keys():
                array_size = pos.cli.array_data[array_name].get("size")
                array_state = pos.cli.array_data[array_name].get("state")
                logger.info(f"Array Size = {array_size} and Status = {array_state}")

            assert array_unmount_and_delete(pos, info_array=True) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_multi_array_max_size_volume(array_fixture):
    """
    Test two RAID5 arrays using hetero devices, Create max size volume on each array.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_max_size_volume ================== "
    )
    try:
        pos = array_fixture
        assert array_create_and_list(pos) == True
        assert volume_create_and_mount_multiple(pos, num_volumes=1) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

array_state = ["DEGRADED", "STOP", "OFFLINE"]
@pytest.mark.regression
@pytest.mark.parametrize("array_state", array_state)
def test_hetero_multi_array_diff_states_rename_vol(array_fixture, array_state):
    """
    Test two RAID5 arrays using hetero devices, Create max size volume on each array.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_diff_states_rename_vol ================== "
    )
    try:
        pos = array_fixture
        assert array_create_and_list(pos) == True
        assert volume_create_and_mount_multiple(pos, num_volumes=1) == True
 
        assert pos.cli.array_list()[0] == True

        vol_dict = {}
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            vol_dict[array_name] = pos.cli.vols[0]

        num_disk_remove = 0
        unmount_array = False
        if array_state == "STOP":
            num_disk_remove = 2
        elif array_state == "DEGRADED":
            num_disk_remove = 1
        elif array_state == "OFFLINE":
            unmount_array = True

        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            if num_disk_remove > 0 :
                data_dev_list =  pos.cli.array_data[array_name]["data_list"]
                remove_drives = data_dev_list[:num_disk_remove]
                assert pos.target_utils.device_hot_remove(device_list=remove_drives)
            elif unmount_array:
                assert pos.cli.array_unmount(array_name=array_name)

        exp_res = False if array_state in ["OFFLINE", "STOP"] else True
        for array_name in pos.cli.array_dict.keys():
            vol_name = vol_dict[array_name] 
            new_vol_name =  f"{vol_name}_new"
            assert pos.cli.volume_rename(new_vol_name, vol_name,
                                         array_name=array_name)[0] == exp_res
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_degraded_array_create_delete_vols(array_fixture):
    """
    Test two RAID5 arrays using hetero devices, Make if degraded and create and delete volume on each array.
    """
    logger.info(
        " ==================== Test : test_hetero_degraded_array_create_delete_vols ================== "
    )
    try:
        pos = array_fixture
        assert array_create_and_list(pos) == True

        # Hot Remove Disk
        for array_name in pos.cli.array_dict.keys():
            data_dev_list =  pos.cli.array_data[array_name]["data_list"]
            remove_drives = data_dev_list[:1]
            assert pos.target_utils.device_hot_remove(device_list=remove_drives)
      
        # Create and delete array from faulty array
        for array_name in pos.cli.array_dict.keys():
            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.volume_create(vol_name, vol_size, 
                                        array_name=array_name)[0] == True
            
            assert pos.cli.volume_delete(vol_name, array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_degraded_array_unmount(array_fixture):
    """
    Create two RAID5 arrays using hetero devices, Make one array degraded and unmount it. 
    It should not impect the other array.
    """
    logger.info(
        " ==================== Test : test_hetero_degraded_array_unmount ================== "
    )
    try:
        pos = array_fixture
        assert array_create_and_list(pos) == True

        # Hot Remove Disk
        for array_name in pos.cli.array_dict.keys():
            data_dev_list =  pos.cli.array_data[array_name]["data_list"]
            remove_drives = data_dev_list[:1]
            assert pos.target_utils.device_hot_remove(device_list=remove_drives)
      
        # Unmount the degraded array
        assert pos.cli.array_unmount(array_name=array_name)[0] == True

        # Get the array info for both array
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.array_info(array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


def array_create_and_list(pos, raid_list=["RAID5", "RAID5"], 
                          num_devs=[RAID5_MIN_DISKS, RAID5_MIN_DISKS]):
    try:
        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for array_index in range(2):
            data_disk_req = {'mix': num_devs[array_index] - 1, 'any': 1}
            assert create_hetero_array(pos, raid_list[array_index], data_disk_req, 
                                       array_index=array_index, array_mount="WT", 
                                       array_info=True) == True
 
        assert pos.cli.array_list()[0] == True
    except Exception as e:
        logger.error(f"Array create and list failed due to {e}")
        traceback.print_exc()
        return False
    return True

