import pytest
import traceback

import logger

logger = logger.get_logger(__name__)

@pytest.mark.regression
def test_hetero_three_raid5_array(array_fixture):
    """
    Test to create three RAID5 arrays using hetero devices. 
    """
    logger.info(
        " ==================== Test : test_hetero_three_raid5_array ================== "
    )
    try:
        pos = array_fixture
        data_dict = pos.data_dict
        # Loop 3 times to create 3 arrays of RAID5 using hetero device
        num_array = 3
        for id in range(num_array):
            array_name = f"array{id+1}"
            if id >= len(data_dict["device"]["uram"]):
                # Create 3rd buffer dev
                uram_name=f"uram{id}"
                numa = data_dict["device"]["uram"][0]["numa_node"]
                bufer_size=data_dict["device"]["uram"][0]["bufer_size"]
                strip_size=data_dict["device"]["uram"][0]["strip_size"]
                assert pos.cli.device_create(uram_name=uram_name, numa=numa,
                        bufer_size=bufer_size, strip_size=strip_size)[0] == True
            else:
                uram_name = data_dict["device"]["uram"][id]["uram_name"]

            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < (num_array - id) * 3:
                pytest.skip(f"Insufficient disk {len(pos.cli.system_disks)}. "\
                            f"Required minimum {(num_array - id) * 3} disk")

            data_device_conf = {'mix': 2, 'any': 1}

            if not pos.target_utils.get_hetero_device(data_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            # The 3rd array creation should fail.  
            res = False if(id == 2) else True

            assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == res

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


@pytest.mark.regression
def test_hetero_offline_array_vol_create(array_fixture):
    """
    Test two RAID5 arrays using hetero devices, Create max size volume from Offline array.
    """
    logger.info(
        " ==================== Test : test_hetero_offline_array_vol_create ================== "
    )
    try:
        pos = array_fixture
        data_dict = pos.data_dict
        # Loop 2 times to create two RAID array of RAID5 using hetero device
        num_array = 2
        assert pos.cli.device_scan()[0] == True
        for id in range(num_array):
            assert pos.cli.device_list()[0] == True
            
            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (num_array - id):
                pytest.skip(f"Insufficient disk {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (num_array - id)} disks")

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

            assert pos.cli.array_info(array_name=array_name)[0] == True

            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol1"
            status = pos.cli.volume_create(vol_name, vol_size, array_name=array_name)
            assert status[0] == False
            event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for volume create due to {event_name}")
            
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


@pytest.mark.regression
def test_hetero_multi_array_delete_mounted_vols(array_fixture):
    """
    Test two RAID5 arrays using hetero devices, Delete mounted volumes.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_delete_mounted_vols ================== "
    )
    try:
        pos = array_fixture
        data_dict = pos.data_dict
        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list
        assert pos.cli.device_scan()[0] == True

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        num_array = 2
        for id in range(num_array):
            assert pos.cli.device_list()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (num_array - id):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (num_array - id)} disk to create array")

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

            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.volume_create(vol_name, vol_size, array_name=array_name)[0] == True
            
            ss_list = [ss for ss in ss_temp_list if f"array{id + 1}" in ss]
            nqn=ss_list[0]
            assert pos.cli.volume_mount(vol_name, array_name, nqn)[0] == True

        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            vol_name = f"{array_name}_pos_vol"
            # Delete mounted volume
            status = pos.cli.volume_delete(vol_name, array_name)
            assert status[0] == False
            event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for volume delete due to {event_name}")

            # Unmount Volume
            assert pos.cli.volume_unmount(vol_name, array_name=array_name)[0] == True

            # Delete Volume
            assert pos.cli.volume_delete(vol_name, array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


@pytest.mark.regression
def test_hetero_faulty_array_create_delete_vols(array_fixture):
    """
    Test two RAID5 arrays using hetero devices, Make it fault and create and delete volume on each array.
    """
    logger.info(
        " ==================== Test : test_hetero_faulty_array_create_delete_vols ================== "
    )
    try:
        pos = array_fixture
        data_dict = pos.data_dict
        # Loop 2 times to create two RAID array of RAID5 using hetero device
        num_array = 2
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True

        # Verify the minimum disk requirement
        if len(pos.cli.system_disks) < 3 * num_array:
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * num_array} disk to create array")
        for index in range(num_array):
            array_name = f"array{index+1}"
            uram_name = data_dict["device"]["uram"][index]["uram_name"]

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
            remove_drives = data_dev_list[:2]
            assert pos.target_utils.device_hot_remove(device_list=remove_drives)
      
        # Create and delete array from faulty array
        for array_name in pos.cli.array_dict.keys():
            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol"
            status = pos.cli.volume_create(vol_name, vol_size, 
                                        array_name=array_name)
            assert status[0] == False
            event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for volume create due to {event_name}")
            
            status = pos.cli.volume_delete(vol_name, array_name)
            assert status[0] == False
            event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for volume create due to {event_name}")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_array_no_raid_without_uram(array_fixture):
    """
    Test to create one array of all RAID type using minimum required devices of 
    different size. Atleast one device of size 20 GiB.
    """
    logger.info(
        " ==================== Test : test_hetero_array_all_raid ================== "
    )
    try:
        pos = array_fixture
        array_name = "array1"
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True

        if len(pos.cli.system_disks) < 1:
            logger.warning("No drive is present, required min 1 drive")

        data_device_conf = {'20GiB':1}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        status = pos.cli.array_create(write_buffer=None, data=data_drives, 
                                    spare=spare_drives, raid_type="no-raid",
                                    array_name=array_name)
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for array create due to {event_name}")

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_multi_array_mount_vol_to_same_subs(array_fixture):
    """
    Test two RAID5 arrays using hetero devices, Create 1 volume and mount to same subsystem.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_mount_vol_to_same_subs ================== "
    )
    try:
        pos = array_fixture
        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list
        nqn = ss_temp_list[0]
        assert pos.cli.device_scan()[0] == True

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        num_array = 2
        for id in range(2):
            assert pos.cli.device_list()[0] == True

            # Verify the minimum disk requirement
            if len(pos.cli.system_disks) < 3 * (num_array - id):
                pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                            f"Required minimum {3 * (num_array - id)} disk to create array")

            array_name = f"array{id+1}"
            uram_name = pos.data_dict["device"]["uram"][id]["uram_name"]

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

        assert pos.cli.array_list()[0] == True
        for id, array_name in enumerate(pos.cli.array_dict.keys()):
            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.volume_create(vol_name, vol_size, array_name=array_name)[0] == True
            
            # Mount the 2nd volume to same subsyste and expect the failure
            exp_res = True
            if id == 1:
                exp_res = False
            assert pos.cli.volume_mount(vol_name, array_name, nqn)[0] == exp_res

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
