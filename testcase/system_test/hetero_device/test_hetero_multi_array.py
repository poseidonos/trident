import pytest
import traceback

from pos import POS
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
            for id in range(2):
                assert pos.cli.device_scan()[0] == True
                assert pos.cli.device_list()[0] == True

                # Verify the minimum disk requirement
                if len(pos.cli.system_disks) < sum(num_devs[id:]):
                    pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                                f"Required minimum {sum(num_devs)}")

                array_name = f"array{id+1}"
                raid_type = raid_types[id]
                num_devices = num_devs[id]
                uram_name = data_dict["device"]["uram"][id]["uram_name"]

                if raid_type.lower() == "raid0" and num_devices == 2:
                    data_device_conf = {'mix': 2}
                else:
                    data_device_conf = {'mix': 2, 'any': num_devices - 2}

                if not pos.target_utils.get_hetero_device(data_device_conf):
                    logger.info("Failed to get the required hetero devcies")
                    pytest.skip("Required condition not met. Refer to logs for more details")

                data_drives = pos.target_utils.data_drives
                spare_drives = pos.target_utils.spare_drives

                assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                            spare=spare_drives, raid_type=raid_type,
                                            array_name=array_name)[0] == True

                assert pos.cli.array_info(array_name=array_name)[0] == True

                assert pos.cli.array_mount(array_name=array_name)[0] == True
                assert pos.cli.array_info(array_name=array_name)[0] == True

                array_size = pos.cli.array_data[array_name].get("size")
                array_state = pos.cli.array_data[array_name].get("state")
                logger.info(f"Array Size = {array_size} and Status = {array_state}")

            # List Array, Unmount and Delete to goto Cleanup for next iteration
            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())
            for array in array_list:
                assert pos.cli.array_unmount(array_name=array)[0] == True
                assert pos.cli.array_delete(array_name=array)[0] == True

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

        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for id in range(2):
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (3 - id):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (3 - id)} disk to create array")

            array_name = f"array{id+1}"
            uram_name = data_dict["device"]["uram"][id]["uram_name"]

            data_device_conf = {'mix': 2, 'any': 1}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == True

            assert pos.cli.array_mount(array_name=array_name)[0] == True
            assert pos.cli.array_info(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_data[array_name].get("size"))
            vol_size = f"{array_size // (1024 * 1024)}mb"  # Volume Size in MB
            vol_name = f"{array_size}_pos_vol"
            assert pos.cli.volume_create(vol_name, vol_size, array_name=array_name)[0] == True

            ss_list = [ss for ss in ss_temp_list if f"subsystem{id + 1}" in ss]
            nqn=ss_list[0]
            assert pos.cli.volume_mount(vol_name, array_name, nqn)[0] == True

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
        assert pos.cli.reset_devel()[0] == True

        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for id in range(2):
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (2 - id):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (2 - id)} disk to create array")

            array_name = f"array{id+1}"
            uram_name = data_dict["device"]["uram"][id]["uram_name"]

            data_device_conf = {'mix': 2, 'any': 1}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == True

            assert pos.cli.array_mount(array_name=array_name)[0] == True
            assert pos.cli.array_info(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_data[array_name].get("size"))
            vol_size = f"{array_size // (1024 * 1024)}mb"  # Volume Size in MB
            vol_name = f"{array_size}_pos_vol"
            assert pos.cli.volume_create(vol_name, vol_size, array_name=array_name)[0] == True

            ss_list = [ss for ss in ss_temp_list if array_name in ss]
            nqn=ss_list[0]
            assert pos.cli.volume_mount(vol_name, array_name, nqn)[0] == True

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

        for array_name in pos.cli.array_dict.keys():
            vol_name = f"{array_size}_pos_vol"
            new_vol_name =  f"{array_size}_pos_vol_new"
            out = pos.cli.volume_rename(new_vol_name, vol_name,
                                        array_name=array_name)[0]
            if array_state in ["OFFLINE", "STOP"]:
                assert out == False
            else:
                assert out == True

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

        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for id in range(2):
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (2 - id):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (2 - id)} disk to create array")

            array_name = f"array{id+1}"
            uram_name = data_dict["device"]["uram"][id]["uram_name"]

            data_device_conf = {'mix': 2, 'any': 1}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == True

            assert pos.cli.array_mount(array_name=array_name)[0] == True
            assert pos.cli.array_info(array_name=array_name)[0] == True

        assert pos.cli.array_list()[0] == True

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

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for id in range(2):
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (2 - id):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (2 - id)} disk to create array")

            array_name = f"array{id+1}"
            uram_name = data_dict["device"]["uram"][id]["uram_name"]

            data_device_conf = {'mix': 2, 'any': 1}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == True

            assert pos.cli.array_mount(array_name=array_name)[0] == True
            assert pos.cli.array_info(array_name=array_name)[0] == True

        assert pos.cli.array_list()[0] == True

        # Hot Remove Disk from first array
        array_name = "array1"
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
