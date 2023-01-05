import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_wt_autocreate_array(setup_cleanup_array_function, raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_autocreate_array  ================== "
    )
    try:
        pos = setup_cleanup_array_function
        array_name = "posarray1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.devel_resetmbr()[0] == True
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        assert (
            pos.cli.array_autocreate(
                buffer_name="uram0",
                num_data=nr_data_drives,
                raid=raid_type,
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.array_unmount(array_name=array_name, write_back=False)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
