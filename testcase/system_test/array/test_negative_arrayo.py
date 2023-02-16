import pytest
import traceback

import logger

logger = logger.get_logger(__name__)


def negative_test_setup_function(pos, nr_data_drives: int):
    try:
        global array_name, system_disks, data_disk_list
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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
    array_fixture, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_array_invalid_data_disk ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        system_disks = ["dummy1", "dummy2", "dummy1"]
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        status = pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)

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
    array_fixture, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_create_array_invalid_commands ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="dummy", data=data_disk_list,
                    spare=[], raid_type=raid_type)[0] == False
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array_less_data_drive(
    array_fixture, raid_type="RAID5", nr_data_drives=2
):
    logger.info(
        " ==================== Test : test_array_less_data_drive ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        status = pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)

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
    array_fixture, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_add_spare_without_array_mount ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)[0] == True

        assert pos.cli.array_addspare(array_name=array_name,
                     device_name=spare_disk_list[0])[0] == False

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_remove_spare_without_array_mount(
    array_fixture, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_remove_spare_without_array_mount ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=spare_disk_list, raid_type=raid_type)[0] == True

        assert pos.cli.array_rmspare(array_name=array_name,
                    device_name=spare_disk_list[0])[0] == False
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array_mnt_without_arrays(array_fixture, nr_data_drives=3):
    logger.info(" ==================== Test : test_array_mnt_without_arrays ================== ")
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        status = pos.cli.array_mount(array_name=array_name, write_back=False)
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
    array_fixture, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_mnt_vol_stop_arrray_state ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)[0] == True

        assert pos.cli.array_mount(array_name=array_name, write_back=True)[0] == True
        assert pos.target_utils.device_hot_remove(data_disk_list[:2]) == True
        assert pos.cli.array_info(array_name)[0] == True
        array_status = pos.cli.array_data[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_data[array_name]["state"] != "STOP":
            logger.error(
                "Expected array state mismatch with output{}".format(
                    array_status["state"]
                )
            )
            assert 0
        else:
            assert (
                pos.cli.volume_create(
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
    array_fixture, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_rename_vol_stop_arrray_state ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)[0] == True

        assert pos.cli.array_mount(array_name=array_name,
                                   write_back=True)[0] == True
        assert pos.cli.volume_create(array_name=array_name,
                        size="10gb", volumename="vol")[0] == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        assert pos.target_utils.device_hot_remove(data_disk_list[:2]) == True
        assert pos.cli.array_info(array_name)[0] == True
        array_status = pos.cli.array_data[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_data[array_name]["state"] != "STOP":
            logger.error(
                "Expected array state mismatch with output{}".format(
                    array_status["state"]
                )
            )
            assert 0
        else:
            assert pos.cli.volume_rename(array_name=array_name,
                                        volname=pos.cli.vols[0],
                                        new_volname="posvol")[0] == False

            logger.info("As expected volume rename failed in array stop state")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_uram_creation_after_scan(array_fixture, nr_data_drives=3):
    logger.info(
        " ==================== Test : test_uram_creation_after_scan ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        assert pos.cli.device_scan()[0] == True
        assert (
            pos.cli.device_create(
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
    array_fixture, raid_type="RAID5", nr_data_drives=3
):
    logger.info(
        " ==================== Test : test_delete_create_array ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)[0] == True
        
        assert pos.target_utils.device_hot_remove(system_disks[:1]) == True
        assert pos.cli.array_delete(array_name=array_name)

        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_logger_info(array_fixture, raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_logger_info ================== "
    )
    try:
        pos = array_fixture
        assert negative_test_setup_function(pos, nr_data_drives) == True
        spare_disk_list = [system_disks.pop()]
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=spare_disk_list, raid_type=raid_type)[0] == True
        assert pos.cli.logger_info()[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
