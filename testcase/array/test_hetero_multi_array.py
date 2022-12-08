import pytest
import traceback

from common_libs import *
import logger

logger = logger.get_logger(__name__)

@pytest.mark.sanity
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

@pytest.mark.sanity
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
            data_dev_list =  pos.cli.array_info[array_name]["data_list"]
            remove_drives = data_dev_list[:1]
            assert pos.target_utils.device_hot_remove(device_list=remove_drives)
      
        # Create and delete array from faulty array
        for array_name in pos.cli.array_dict.keys():
            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.create_volume(vol_name, vol_size, 
                                        array_name=array_name)[0] == True
            
            assert pos.cli.delete_volume(vol_name, array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.sanity
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
            data_dev_list =  pos.cli.array_info[array_name]["data_list"]
            remove_drives = data_dev_list[:1]
            assert pos.target_utils.device_hot_remove(device_list=remove_drives)
      
        # Unmount the degraded array
        assert pos.cli.unmount_array(array_name=array_name)[0] == True

        # Get the array info for both array
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.info_array(array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


def array_create_and_list(pos):
    try:
        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for array_index in range(2):
            data_disk_req = {'mix': 2, 'any': 1}
            assert create_hetero_array(pos, "RAID5", data_disk_req, 
                                       array_index=array_index, mount_array="WT", 
                                       info_array=True) == True
 
        assert pos.cli.list_array()[0] == True
    except Exception as e:
        logger.error(f"Array create and list failed due to {e}")
        traceback.print_exc()
        return False
    return True

