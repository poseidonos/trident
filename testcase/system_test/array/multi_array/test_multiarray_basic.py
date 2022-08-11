import pytest

from pos import POS
import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict

    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True

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
def test_create_array3_after_array2_delete():
    logger.info(
        " ==================== Test : test_create_array3_after_array2_delete ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = f"pos_array"
        spare_disk_list = []
        data_disk_array = ([], []) 

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert  pos.cli.mount_array(array_name=array_name)[0] == True
        
        # Unmount both Arrays
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            assert pos.cli.unmount_array(array_name=array_name)[0] == True

        # Delete 2nd Array
        array_name = f"{array_name_pre}_1"
        assert pos.cli.delete_array(array_name=array_name)[0] == True
        
        # Create 3rd Array
        array_name = f"{array_name_pre}_3"
        uram_name = f"uram0"
        assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[0],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multiarray_add_max_spare():
    logger.info(
        " ==================== Test : test_multiarray_add_max_spare ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1 * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = f"pos_array"
        spare_disk_list = []
        data_disk_array = ([], []) 

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        spare_disk_list[0].append(system_disks.pop(0))
        spare_disk_list[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert  pos.cli.mount_array(array_name=array_name)[0] == True

        for id in range(len(system_disks)):
            array_name = f"{array_name_pre}_{(id % 2) + 1}"
            device_name = system_disks.pop(0)
            assert pos.cli.addspare_array(device_name=device_name, 
                                        array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_unmount_array_unmount_vol():
    logger.info(
        " ==================== Test : test_multiarray_unmount_array_unmount_vol ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = f"pos_array"
        vol_name_pre = "pos_vol"
        spare_disk_list = []
        data_disk_array = ([], [])
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:2]

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True

            assert pos.cli.create_volume(vol_name, array_name=array_name,
                                                     size="10gb")[0] == True
            assert pos.cli.mount_volume(vol_name, array_name, nqn=ss_list[id])[0] == True

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.unmount_array(array_name=array_name)[0] == True

            # The volume unmount is expected to fail as array is already unmounted
            # TODO handle exception at API side
            try:
                assert pos.cli.unmount_volume(vol_name, array_name=array_name) == False
            except:
                logger.info("Expected fail for unmount volume - array is unmounted. {e}")
                                    
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_delete_array_list_vol():
    logger.info(
        " ==================== Test : test_multiarray_delete_array_list_vol ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = f"pos_array"
        vol_name_pre = "pos_vol"
        spare_disk_list = []
        data_disk_array = ([], [])
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:2]

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True

            assert pos.cli.create_volume(vol_name, array_name=array_name,
                                                     size="10gb")[0] == True
            assert pos.cli.mount_volume(vol_name, array_name, nqn=ss_list[id])[0] == True

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
            assert pos.cli.delete_array(array_name=array_name)[0] == True

            # Expected fail for list volume as array is already deleted
            # TODO handle exception as API level
            try:
                assert pos.cli.list_volume(vol_name) == False
            except Exception as e:
                logger.info("Expected fail for list volume - array is deleted. {e}")
                                    
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_recreate_array_and_vol():
    logger.info(
        " ==================== Test : test_multiarray_recreate_array_and_vol ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = f"pos_array"
        vol_name_pre = "pos_vol"
        spare_disk_list = []
        data_disk_array = ([], [])
        array_size_list=[]
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:2]

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_info[array_name].get("size"))
            array_size_list.append(array_size)
            vol_size = f"{array_size // (1024 * 1024)}mb"  # Volume Size in MB

            assert pos.cli.create_volume(vol_name, array_name=array_name,
                                                     size=vol_size)[0] == True
            assert pos.cli.mount_volume(vol_name, array_name, nqn=ss_list[id])[0] == True

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
            assert pos.cli.delete_array(array_name=array_name)[0] == True

        for id in range(2): 
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            vol_name = f"{array_name}_{vol_name_pre}"

            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            # Create the volume of same size which created with deleted array
            array_size = array_size_list[id]
            vol_size = f"{array_size // (1024 * 1024)}mb"  # Volume Size in MB

            assert pos.cli.create_volume(vol_name, array_name=array_name,
                                        size=vol_size)[0] == True
            assert pos.cli.mount_volume(vol_name, array_name, nqn=ss_list[id])[0] == True
                                    
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multiarray_mount_unmount_loop():
    logger.info(
        " ==================== Test : test_multiarray_mount_unmount_loop ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = f"pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])
        assert pos.target_utils.get_subsystems_list() == True

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True
                                    
        loop_limit = 20
        for loop_counter in range(loop_limit):
            for id in range(2):
                array_name = f"{array_name_pre}_{id+1}"
                assert pos.cli.unmount_array(array_name=array_name)[0] == True
                assert pos.cli.mount_array(array_name=array_name)[0] == True
                assert pos.cli.info_array(array_name=array_name)[0] == True

            logger.info("*" * 50)
            logger.info(f"Loop completed: {loop_counter + 1}/{loop_limit}.")
            logger.info("*" * 50)

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)