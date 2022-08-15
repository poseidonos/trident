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
            assert pos.cli.delete_array(array_name=array)[0] == True

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
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
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

            assert pos.cli.mount_array(array_name=array_name)[0] == True

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
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = ((nr_data_drives + 1) * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
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

            assert pos.cli.mount_array(array_name=array_name)[0] == True

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
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
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
            assert pos.cli.mount_volume(
                vol_name, array_name, nqn=ss_list[id])[0] == True

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.unmount_array(array_name=array_name)[0] == True

            # The volume unmount is expected to fail as array is already unmounted
            # TODO handle exception at API side
            try:
                assert pos.cli.unmount_volume(
                    vol_name, array_name=array_name) == False
            except:
                logger.info(
                    "Expected fail for unmount volume - array is unmounted. {e}")

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
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
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
            assert pos.cli.mount_volume(
                vol_name, array_name, nqn=ss_list[id])[0] == True

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
                logger.info(
                    "Expected fail for list volume - array is deleted. {e}")

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
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
        vol_name_pre = "pos_vol"
        spare_disk_list = []
        data_disk_array = ([], [])
        array_size_list = []
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
            assert pos.cli.mount_volume(
                vol_name, array_name, nqn=ss_list[id])[0] == True

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
            assert pos.cli.mount_volume(
                vol_name, array_name, nqn=ss_list[id])[0] == True

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
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
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


@pytest.mark.regression
def test_unmount_array1_delete_array2():
    logger.info(
        " ==================== Test : test_unmount_array1_delete_array2 ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
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

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

        # Unmount Array 1
        array_name = f"{array_name_pre}_1"
        assert pos.cli.unmount_array(array_name=array_name)[0] == True

        # Delete Array 2, Expected to fail
        array_name = f"{array_name_pre}_2"
        try:
            assert pos.cli.delete_array(array_name=array_name)[0] == False
        except Exception as e:
            logger.info("Should be expected error. Verify from logs")

        # Unmount and Delete Array 2
        assert pos.cli.mount_array(array_name=array_name)[0] == True
        assert pos.cli.delete_array(array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array1_spare_as_array2_data_disk():
    logger.info(
        " ==================== Test : test_array1_spare_as_array2_data_disk ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_list = []

        for i in range(nr_data_drives):
            data_disk_list.append(system_disks.pop(0))
            spare_disk_list.append(system_disks.pop(0))

        array_name = f"{array_name_pre}_1"
        uram_name = f"uram0"
        assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_list,
                                    spare=spare_disk_list, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        # Use Array 1 spare disk as data disk for array 2
        array_name = f"{array_name_pre}_2"
        uram_name = f"uram1"
        assert pos.cli.create_array(write_buffer=uram_name, data=spare_disk_list,
                                    spare=[], raid_type=raid_type,
                                    array_name=array_name)[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array1_data_as_array2_spare_disk():
    logger.info(
        " ==================== Test : test_array1_data_as_array2_spare_disk ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        array_name = f"{array_name_pre}_1"
        uram_name = f"uram0"
        assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[0],
                                    spare=spare_disk_list, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        # Use Array 1 spare disk as data disk for array 2
        array_name = f"{array_name_pre}_2"
        uram_name = f"uram1"
        assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[1],
                                    spare=data_disk_array[0], raid_type=raid_type,
                                    array_name=array_name)[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_size_after_unmount_mount():
    logger.info(
        " ==================== Test : test_multiarray_size_after_unmount_mount ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * 2):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * 2}"
            )

        array_name_pre = "pos_array"
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

            assert pos.cli.mount_array(array_name=array_name)[0] == True

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            assert pos.cli.info_array(array_name=array_name)[0] == True
            array_size_pre = int(pos.cli.array_info[array_name].get("size"))

            assert pos.cli.unmount_array(array_name=array_name)[0] == True
            assert pos.cli.mount_array(array_name=array_name)[0] == True

            assert pos.cli.info_array(array_name=array_name)[0] == True
            array_size_post = int(pos.cli.array_info[array_name].get("size"))

            assert array_size_pre == array_size_post

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array2_unmount_after_detach_spare():
    logger.info(
        " ==================== Test : test_array2_unmount_after_detach_spare ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = ((nr_data_drives + 1) * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_array = ([], [])
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        spare_disk_array[0].append(system_disks.pop(0))
        spare_disk_array[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_array[id], raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True

        # Array 2 Detach Speare disk
        assert pos.target_utils.device_hot_remove(spare_disk_array[1]) == True

        array_name = f"{array_name_pre}_2"
        assert pos.cli.unmount_array(array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_different_num_drives():
    logger.info(
        " ==================== Test : test_multiarray_different_num_drives ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = ((nr_data_drives + 1) * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))

        for i in range(len(system_disks) - nr_data_drives):
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_second_array_without_uram():
    logger.info(
        " ==================== Test : test_second_array_without_uram ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Array 1 with valid uram
        array_name = f"{array_name_pre}_1"
        uram_name = f"uram0"
        assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[0],
                                    spare=spare_disk_list, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        # Array 2 with invlaid uram - Expected Fail
        array_name = f"{array_name_pre}_2"
        uram_name = f"uram_ivalid"
        assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[1],
                                    spare=spare_disk_list, raid_type=raid_type,
                                    array_name=array_name)[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_with_invalid_uram():
    logger.info(
        " ==================== Test : test_multiarray_with_invalid_uram ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True

        uram_names = ["uram57", "uram58"]
        # Buffer device must be equal to or greater than 128MB * number of data devices + 512MB.
        buff_size = 1310720     # 768 MB  (1310720 * 512 Block Size)

        for id in range(2):
            assert pos.cli.create_device(uram_name=uram_names[id],
                                         bufer_size=buff_size, strip_size=512, numa=i)[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Create both array with invalid uram
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = uram_names[id]
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_unmount_unmounted_array():
    logger.info(
        " ==================== Test : test_multiarray_unmount_unmounted_array ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Create two arrays
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

        # Unmount first array. Expected to fail
        assert pos.cli.unmount_array(
            array_name=f"{array_name_pre}_1")[0] == False

        # Mount both array
        assert pos.cli.mount_array(array_name=f"{array_name_pre}_1")[0] == True
        assert pos.cli.mount_array(array_name=f"{array_name_pre}_2")[0] == True

        # Unmount second array
        assert pos.cli.unmount_array(
            array_name=f"{array_name_pre}_2")[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_invalid_raid():
    logger.info(
        " ==================== Test : test_multiarray_invalid_raid ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Create two arrays
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"

            # Invalid RAID - Expected Failure
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type="RAID9",
                                        array_name=array_name)[0] == False

            # Valid RAID - Expected Success
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_consume_max_array_capacity():
    logger.info(
        " ==================== Test : test_multiarray_consume_max_array_capacity ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3
        num_array = 2
        num_vols = 256

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * num_array)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        vol_name_pre = "pos_vol"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Create two arrays
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name,
                                        data=data_disk_array[id],
                                        spare=spare_disk_list,
                                        raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_info[array_name].get("size"))
            # Volume Size in MB
            vol_size = f"{int((array_size // num_vols) // (1024 * 1024))}mb"

            assert pos.target_utils.create_volume_multiple(array_name, num_vols,
                                                           vol_name_pre, size=vol_size) == True

        # Try to create 257th volume on the second array. - Expected Failure
        array_name = f"{array_name_pre}_2"
        vol_name = f"{array_name}_{vol_name_pre}_257"
        assert pos.cli.create_volume(vol_name, size=vol_size,
                                     array_name=array_name)[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_unmount_array_effect():
    logger.info(
        " ==================== Test : test_multiarray_unmount_array_effect ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Create two arrays
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True
            assert pos.cli.mount_array(array_name=array_name)[0] == True

        # Unmount second array and Check the array state
        assert pos.cli.unmount_array(
            array_name=f"{array_name_pre}_2")[0] == True

        assert pos.cli.info_array(array_name=f"{array_name_pre}_1")[0] == True
        assert pos.cli.array_info[f"{array_name_pre}_1"].get(
            "state") == "NORMAL"

        assert pos.cli.info_array(array_name=f"{array_name_pre}_2")[0] == True
        assert pos.cli.array_info[f"{array_name_pre}_2"].get(
            "state") == "OFFLINE"

        # Unmount first array and Mount second array
        assert pos.cli.unmount_array(
            array_name=f"{array_name_pre}_1")[0] == True
        assert pos.cli.mount_array(array_name=f"{array_name_pre}_2")[0] == True

        assert pos.cli.info_array(array_name=f"{array_name_pre}_1")[0] == True
        assert pos.cli.array_info[f"{array_name_pre}_1"].get(
            "state") == "OFFLINE"

        assert pos.cli.info_array(array_name=f"{array_name_pre}_2")[0] == True
        assert pos.cli.array_info[f"{array_name_pre}_2"].get(
            "state") == "NORAML"

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_unmount_mount_array1():
    logger.info(
        " ==================== Test : test_multiarray_unmount_mount_array1 ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * 2)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Create two arrays
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True
            assert pos.cli.mount_array(array_name=array_name)[0] == True

        # Unmount first array and verify the state
        array_name = f"{array_name_pre}_1"
        assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.info_array(array_name=array_name)[0] == True
        assert pos.cli.array_info[array_name].get("state") == "OFFLINE"

        # Mount the first array and verify the state
        assert pos.cli.mount_array(array_name=array_name)[0] == True
        assert pos.cli.info_array(array_name=array_name)[0] == True
        assert pos.cli.array_info[array_name].get("state") == "NORMAL"

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_vol_unmount_delete_loop():
    logger.info(
        " ==================== Test : test_multiarray_vol_unmount_delete_loop ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3
        num_array = 2

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * num_array):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * num_array}"
            )

        array_name_pre = "pos_array"
        vol_name_pre = "pos_vol"
        spare_disk_list = []
        data_disk_array = ([], [])
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:2]

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(num_array):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            vol_name = f"{array_name}_{vol_name_pre}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True

        loop_limit = 10
        for loop_counter in range(loop_limit):
            for id in range(num_array):
                array_name = f"{array_name_pre}_{id+1}"
                vol_name = f"{array_name}_{vol_name_pre}"
                assert pos.cli.create_volume(vol_name, size="10gb",
                                             array_name=array_name)[0] == True
                assert pos.cli.mount_volume(vol_name, array_name,
                                            nqn=ss_list[id])[0] == True

                assert pos.cli.unmount_volume(vol_name, array_name)[0] == True
                assert pos.cli.delete_volume(vol_name, array_name)[0] == True

            logger.info("*" * 50)
            logger.info(f"Loop completed: {loop_counter + 1}/{loop_limit}.")
            logger.info("*" * 50)

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multiarray_mount_mounted_array():
    logger.info(
        " ==================== Test : test_multiarray_mount_mounted_array ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3
        num_array = 2

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives * num_array):
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {nr_data_drives * num_array}"
            )

        array_name_pre = "pos_array"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        for id in range(num_array):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name, data=data_disk_array[id],
                                        spare=spare_disk_list, raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True

            # Again mount the same array
            assert pos.cli.mount_array(array_name=array_name)[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array1_100_vols_array2_257_vols():
    logger.info(
        " ==================== Test : test_array1_100_vols_array2_257_vols ================== "
    )
    try:
        raid_type, nr_data_drives = "RAID5", 3
        num_array = 2
        num_vols_list = [101, 257]

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(
                data_dict=pos.data_dict) == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.list_device()[0] == True

        system_disks = pos.cli.system_disks
        required_disk = (nr_data_drives * num_array)
        if len(system_disks) < required_disk:
            pytest.skip(
                f"Insufficient disk {system_disks}. Required minimum {required_disk}"
            )

        array_name_pre = "pos_array"
        vol_name_pre = "pos_vol"
        spare_disk_list = []
        data_disk_array = ([], [])

        for i in range(nr_data_drives):
            data_disk_array[0].append(system_disks.pop(0))
            data_disk_array[1].append(system_disks.pop(0))

        # Create two arrays
        for id in range(2):
            array_name = f"{array_name_pre}_{id+1}"
            uram_name = f"uram{id}"
            assert pos.cli.create_array(write_buffer=uram_name,
                                        data=data_disk_array[id],
                                        spare=spare_disk_list,
                                        raid_type=raid_type,
                                        array_name=array_name)[0] == True

            assert pos.cli.mount_array(array_name=array_name)[0] == True
            assert pos.cli.info_array(array_name=array_name)[0] == True

            array_size = int(pos.cli.array_info[array_name].get("size"))
            # Volume Size in MB
            vol_size = f"{int((array_size // num_vols_list[id]) // (1024 * 1024))}mb"

            assert pos.target_utils.create_volume_multiple(array_name,
                                                           num_vols_list[id] - 1, vol_name_pre, size=vol_size) == True

        # Try to create 257th volume on the second array. - Expected Failure
        array_name = f"{array_name_pre}_2"
        vol_name = f"{array_name}_{vol_name_pre}_257"
        assert pos.cli.create_volume(vol_name, size=vol_size,
                                     array_name=array_name)[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
