import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 4), ("RAID10", 2)],
)
def test_wt_multi_array_256vols(
    array_fixture, raid_type, nr_data_drives
):
    """The purpose of this test case is to Create 2 array in Write Through mode. Create and mount 256 volume on each array"""
    logger.info(
        " ==================== Test : test_wt_multi_array_256vols ================== "
    )
    try:
        pos = array_fixture
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
            res = pos.cli.array_create(array_name=array,
                                       write_buffer=f"uram{index}", 
                                       data=data_disk_list,
                                       spare=[], raid_type=raid_type)
            
            assert res[0] == True
            assert pos.cli.array_mount(array_name=array,
                                       write_back=False)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name=array,
                        num_vol=256, size="10gb", vol_name="vol") == True

            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.volume_list(array_name=array)[0] == True
            nqn = pos.target_utils.ss_temp_list[index]
            assert pos.target_utils.mount_volume_multiple(array_name=array,
                             volume_list=pos.cli.vols, nqn=nqn) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
