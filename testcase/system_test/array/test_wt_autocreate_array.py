import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 2), ("RAID10", 4)],
)
def test_wt_autocreate_array(array_fixture, raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_autocreate_array  ================== "
    )
    try:
        pos = array_fixture
        array_name = "posarray1"
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        assert pos.cli.array_autocreate(array_name,
                        buffer_name="uram0", 
                        num_data=nr_data_drives,
                        raid_type=raid_type)[0] == True
        
        assert pos.cli.array_mount(array_name=array_name, write_back=False)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
