import pytest
import traceback

from lib.pos import POS
import logger

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, min_hetero_dev
    pos = POS("pos_config.json")

    data_dict = pos.data_dict

    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
def test_hetero_three_raid5_array():
    """
    Test to create three RAID5 arrays using hetero devices
    """
    logger.info(
        " ==================== Test : test_hetero_three_raid5_array ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        # Loop 3 times to create 3 arrays of RAID5 using hetero device
        num_array = 3
        for id in range(num_array):
            array_name = f"array{id+1}"
            uram_name = data_dict["device"]["uram"][id]["uram_name"]
            if id == 2:
                # Create 3rd buffer dev
                uram_name=f"uram{id}"
                numa = id % 2
                assert pos.cli.create_device(uram_name=uram_name, numa=numa,
                            bufer_size="8388608", strip_size="512")[0] == True

            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

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

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == res

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )


@pytest.mark.regression
def test_hetero_offline_array_vol_create():
    """
    Test two RAID5 arrays using hetero devices, Create max size volume from Offline array.
    """
    logger.info(
        " ==================== Test : test_hetero_offline_array_vol_create ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        num_array = 2
        for id in range(num_array):
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True
            
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

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == True

            assert pos.cli.info_array(array_name=array_name)[0] == True

            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol1"
            assert pos.cli.create_volume(vol_name, vol_size, array_name=array_name)[0] == False

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_multi_array_delete_mounted_vols():
    """
    Test two RAID5 arrays using hetero devices, Delete mounted volumes.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_delete_mounted_vols ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        num_array = 2
        for id in range(2):
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

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

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.create_volume(vol_name, vol_size, array_name=array_name)[0] == True
            
            ss_list = [ss for ss in ss_temp_list if f"subsystem{id + 1}" in ss]
            nqn=ss_list[id]
            assert pos.cli.mount_volume(vol_name, array_name, nqn)[0] == True

        assert pos.cli.list_array()[0] == True
        for array_name in pos.cli.array_disks.keys():
            vol_name = f"{array_name}_pos_vol"
            # Delete mounted volume
            assert pos.cli.delete_volume(vol_name, array_name)[0] == False

            # Unmount Volume
            assert pos.cli.unmount_volume(vol_name, array_name=array_name)[0] == True

            # Delete Volume
            assert pos.cli.delete_volume(vol_name, array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_faulty_array_create_delete_vols():
    """
    Test two RAID5 arrays using hetero devices, Make it fault and create and delete volume on each array.
    """
    logger.info(
        " ==================== Test : test_hetero_faulty_array_create_delete_vols ================== "
    )
    try:
        assert pos.cli.reset_devel()[0] == True

        # Loop 2 times to create two RAID array of RAID5 using hetero device
        num_array = 2
        for id in range(num_array):
            assert pos.cli.scan_device()[0] == True
            assert pos.cli.list_device()[0] == True

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

            assert pos.cli.create_array(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type="RAID5",
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

        assert pos.cli.list_array()[0] == True

        # Hot Remove Disk
        for array_name in pos.cli.array_dict.keys():
            data_dev_list =  pos.cli.array_info[array_name]["data_list"]
            remove_drives = data_dev_list[:2]
            assert pos.target_utils.device_hot_remove(device_list=remove_drives)
      
        # Create and delete array from faulty array
        for array_name in pos.cli.array_dict.keys():
            vol_size = "1G"
            vol_name = f"{array_name}_pos_vol"
            assert pos.cli.create_volume(vol_name, vol_size, 
                                        array_name=array_name)[0] == False
            
            assert pos.cli.delete_volume(vol_name, array_name)[0] == False

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()

    logger.info(
        " ============================= Test ENDs ======================================"
    )

@pytest.mark.regression
def test_hetero_array_no_raid_without_uram():
    """
    Test to create one array of all RAID type using minimum required devices of 
    different size. Atleast one device of size 20 GiB.
    """
    logger.info(
        " ==================== Test : test_hetero_array_all_raid ================== "
    )
    try:
        array_name = "array1"

        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        if len(pos.cli.system_disks) < 1:
            logger.warning("No drive is present, required min 1 drive")

        data_device_conf = {'20GiB':1}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert pos.cli.create_array(write_buffer=None, data=data_drives, 
                                    spare=spare_drives, raid_type="no-raid",
                                    array_name=array_name)[0] == False

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )