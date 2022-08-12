import pytest

from pos import POS
import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("wt_array.json")
    data_dict = pos.data_dict
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
def test_array_invalid_data_disk(raid_type="RAID5", nr_data_drives=3):
    logger.info(" ==================== Test : test_array_invalid_drives ================== ")
    try:
        array_name = "posarray1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = ["dummy1","dummy2","dummy1"]
        if len(system_disks) < (nr_data_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        status = pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )
        assert status[0] == False
        logger.info("As expected testcases failed due to {}".format(status[1]["output"]["Response"]["result"]["status"]["eventName"]))
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_create_array_invalid_commands(raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        array_name = "posarray1"
        assert (
            pos.cli.create_array(
                write_buffer="dummy",
                data=data_disk_list,
                spare=None,
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == False
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_less_data_drive(raid_type="RAID5", nr_data_drives=2):
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        array_name = "posarray1"
        status = pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )
        assert status[0] == False
        logger.info("As expected testcases failed due to {}".format(status[1]["output"]["Response"]["result"]["status"]["eventName"]))
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_add_spare_without_mount(raid_type="RAID5", nr_data_drives=3):
    logger.info(" ==================== Test : test_array_cli_wt ================== ")
    try:
        array_name = "posarray1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (3):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = [system_disks.pop()]
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.addspare_array(array_name=array_name,device_name=spare_disk_list[0])[0] == False
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_mnt_without_arrays(nr_data_drives=3):
    logger.info(" ==================== Test : test_array_cli_wt ================== ")
    try:
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

        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == False
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_add_spare_without_arrays_mnt(raid_type="RAID5", nr_data_drives=3):
    logger.info(" ==================== Test : test_array_cli_wt ================== ")
    try:
        array_name = "posarray1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (3):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = [system_disks.pop()]
        pos.target_utils.device_hot_remove(spare_disk_list)
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
        assert pos.cli.addspare_array(array_name=array_name,device_name=spare_disk_list[0]) == False
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_create_array_no_buffer(raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        array_name = "posarray1"
        assert (
            pos.cli.create_array(
                write_buffer=None,
                data=data_disk_list,
                spare=None,
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == False
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_mnt_vol_fault_arrray_state(raid_type="RAID5", nr_data_drives=3):
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        array_name = "posarray1"
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.target_utils.device_hot_remove([data_disk_list[0]]) == True
        assert pos.target_utils.device_hot_remove([data_disk_list[1]]) == True
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_info[array_name]["state"] != "STOP":
            logger.error("Expected array state mismatch with output{}".format(array_status["state"]))
            assert 0
        else:
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array_name, num_vol=1, size="10gb", vol_name="vol"
                )
                == False
            )
            logger.info("As expected volume creation failed in array stop state")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
