import pytest
import traceback

import logger

logger = logger.get_logger(__name__)


def negative_test_setup_function(pos, nr_data_drives: int):
    try:
        global array_name, system_disks, data_disk_list
        array_name = "posarray1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        return True

    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False


@pytest.mark.regression
def test_array_invalid_data_disk(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_array_invalid_drives ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        system_disks = ["dummy1", "dummy2", "dummy1"]
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        status = pos.cli.create_array(
            write_buffer="uram0",
            data=data_disk_list,
            spare=[],
            raid_type=raid_type,
            array_name=array_name,
        )
        assert status[0] == False
        logger.info(
            "As expected testcases failed due to {}".format(
                status[1]["output"]["Response"]["result"]["status"]["eventName"]
            )
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_create_array_invalid_commands(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_create_array_invalid_commands ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert (
            pos.cli.create_array(
                write_buffer="dummy",
                data=data_disk_list,
                spare=[],
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == False
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array_less_data_drive(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=2
):
    logger.info(
        " ==================== Test : test_array_less_data_drive ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        status = pos.cli.create_array(
            write_buffer="uram0",
            data=data_disk_list,
            spare=[],
            raid_type=raid_type,
            array_name=array_name,
        )
        assert status[0] == False
        logger.info(
            "As expected testcases failed due to {}".format(
                status[1]["output"]["Response"]["result"]["status"]["eventName"]
            )
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_add_spare_without_array_mount(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_add_spare_without_mount ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=[],
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert (
            pos.cli.addspare_array(
                array_name=array_name, device_name=spare_disk_list[0]
            )[0]
            == False
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_remove_spare_without_array_mount(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_add_spare_without_mount ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=spare_disk_list,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert (
            pos.cli.rmspare_array(
                array_name=array_name, device_name=spare_disk_list[0]
            )[0]
            == False
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array_mnt_without_arrays(setup_cleanup_array_function, nr_data_drives=3):
    logger.info(" ==================== Test : test_array_cli_wt ================== ")
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        status = pos.cli.mount_array(array_name=array_name, write_back=False)
        assert status[0] == False
        logger.info(
            "As expected testcases failed due to {}".format(
                status[1]["output"]["Response"]["result"]["status"]["description"]
            )
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_mnt_vol_stop_arrray_state(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=[],
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert pos.target_utils.device_hot_remove(data_disk_list[:2]) == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_info[array_name]["state"] != "STOP":
            logger.error(
                "Expected array state mismatch with output{}".format(
                    array_status["state"]
                )
            )
            assert 0
        else:
            assert (
                pos.cli.create_volume(
                    array_name=array_name, size="10gb", volumename="vol"
                )[0]
                == False
            )
            logger.info("As expected volume creation failed in array stop state")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_rename_vol_stop_arrray_state(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=[],
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert (
            pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[
                0
            ]
            == True
        )
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        assert pos.target_utils.device_hot_remove(data_disk_list[:2]) == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_info[array_name]["state"] != "STOP":
            logger.error(
                "Expected array state mismatch with output{}".format(
                    array_status["state"]
                )
            )
            assert 0
        else:
            assert (
                pos.cli.rename_volume(
                    array_name=array_name, volname=pos.cli.vols[0], new_volname="posvol"
                )[0]
                == False
            )
            logger.info("As expected volume rename failed in array stop state")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_uram_creation_after_scan(setup_cleanup_array_function, nr_data_drives=3):
    logger.info(
        " ==================== Test : test_uram_creation_after_scan ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert pos.cli.scan_device()[0] == True
        assert (
            pos.cli.create_device(
                uram_name="uram2", bufer_size=8388608, strip_size=512, numa=0
            )[0]
            == True
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_delete_create_array(
    setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_add_spare_without_mount ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=[],
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.target_utils.device_hot_remove(system_disks[:1]) == True
        assert pos.cli.delete_array(array_name=array_name)
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=[],
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_logger_info(setup_cleanup_array_function, raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_add_spare_without_mount ================== "
    )
    try:
        pos = setup_cleanup_array_function
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=[],
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.info_logger()[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
