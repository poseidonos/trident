import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_array_wt_wb_loop(setup_cleanup_array_function, raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        pos = setup_cleanup_array_function
        array_name = "array1"
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
        spare_disk_list = []

        if raid_type.upper() == "NORAID":
            raid_type = "no-raid"

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

        for i in range(5):
            assert (
                pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True
            )
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
            assert (
                pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
            )
            assert pos.cli.unmount_array(array_name=array_name)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_array_cli_wt(setup_cleanup_array_function, raid_type, nr_data_drives):
    logger.info(" ==================== Test : test_array_cli_wt ================== ")
    try:
        pos = setup_cleanup_array_function
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
        spare_disk_list = []
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
        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_array_nouram(setup_cleanup_array_function, raid_type, nr_data_drives):
    logger.info(" ==================== Test : test_array_nouram ================== ")
    try:
        pos = setup_cleanup_array_function
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
        spare_disk_list = []
        # creating array without Uram
        assert (
            pos.cli.create_array(
                write_buffer=None,
                data=data_disk_list,
                spare=spare_disk_list,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == False
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pass
        pos.exit_handler(expected=False)
