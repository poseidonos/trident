import pytest
import traceback

from common_libs import *
import logger

logger = logger.get_logger(__name__)

array = [("RAID5", 3),]

@pytest.mark.regression
@pytest.mark.parametrize("repeat_ops", [5])
@pytest.mark.parametrize("raid_type, num_devs", array)
def test_hetero_multi_array_npor_mounted_array(array_fixture, raid_type, num_devs, repeat_ops):
    """
    Create and mount two RAID5 (Default) arrays using 3 (default) number of hetero devices.
    Peform NPOR and verify array are mounted. Unmount and delete arrays. Repeat 5 times.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_npor_mounted_array ================== "
    )
    try:
        pos = array_fixture
        for i in range(repeat_ops):
            num_array = 2
            # Loop 2 times to create two RAID array of RAID5 using hetero device
            for array_index in range(num_array):
                data_disk_req = {'mix': 2, 'any': num_devs - 2}
                assert create_hetero_array(pos, raid_type, data_disk_req,
                                       array_index=array_index, array_mount="WT", 
                                       array_info=True) == True
 
            assert pos.target_utils.npor() == True

            assert array_unmount_and_delete(pos) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
@pytest.mark.parametrize("array_raid, num_devs", array)
def test_hetero_array_spor(array_fixture, array_raid, num_devs):
    """
    Test create single array of selected raid type and num of disk using hetero 
    devices. Run IO and do SPOR. 
    """
    logger.info(
        " ==================== Test : test_hetero_array_spor ================== "
    )
    try:
        pos = array_fixture

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list
 
        data_disk_req = {'mix': 2, 'any': num_devs - 2}
        assert create_hetero_array(pos, array_raid, data_disk_req,
                                   array_index=0, array_mount="WT", 
                                   array_info=True) == True
 
        assert volume_create_and_mount_multiple(pos, num_volumes=1) == True

        assert vol_connect_and_run_random_io(pos, subs_list, time_based=True) == True

        assert pos.target_utils.spor(uram_backup=False) == True
        
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
@pytest.mark.parametrize("fio_runtime", [120])
@pytest.mark.parametrize("array_raid, num_devs", array)
def test_hetero_multi_array_spor(array_fixture, array_raid, num_devs, fio_runtime):
    """
    Test to create multi arrays of selected raid type and num of disk using hetero 
    devices. Run IO and do SPOR. 
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_spor ================== "
    )
    try:
        pos = array_fixture

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        # Create two RAID array of RAID5 using hetero device
        num_array = 2
        for array_index in range(num_array):
            data_disk_req = {'mix': 2, 'any': num_devs - 2}
            assert create_hetero_array(pos, array_raid, data_disk_req,
                                       array_index=array_index, array_mount="WT", 
                                       array_info=True) == True

        assert volume_create_and_mount_multiple(pos, num_volumes=2) == True

        assert vol_connect_and_run_random_io(pos, subs_list, time_based=True,
                                             run_time=fio_runtime) == True

        assert pos.target_utils.spor() == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
