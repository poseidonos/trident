import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("NORAID", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_array_wt_wb_loop(array_fixture, raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        pos = array_fixture
        array_name = "array1"
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
            pos.cli.array_create(
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
                pos.cli.array_mount(array_name=array_name, write_back=False)[0] == True
            )
            assert pos.cli.array_unmount(array_name=array_name)[0] == True
            assert (
                pos.cli.array_mount(array_name=array_name, write_back=True)[0] == True
            )
            assert pos.cli.array_unmount(array_name=array_name)[0] == True

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
def test_array_cli_wt(array_fixture, raid_type, nr_data_drives):
    logger.info(" ==================== Test : test_array_cli_wt ================== ")
    try:
        pos = array_fixture
        array_name = "posarray1"
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = []
        assert (
            pos.cli.array_create(
                write_buffer="uram0",
                data=data_disk_list,
                spare=spare_disk_list,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.array_mount(array_name=array_name, write_back=False)[0] == True
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
def test_array_nouram(array_fixture, raid_type, nr_data_drives):
    logger.info(" ==================== Test : test_array_nouram ================== ")
    try:
        pos = array_fixture
        array_name = "posarray1"
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = []
        # creating array without Uram
        assert (
            pos.cli.array_create(
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
