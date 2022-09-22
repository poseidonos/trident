import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID5", 3), ("RAID10", 4), ("RAID10", 2)],
)
def test_wt_multi_array_256vols(
    setup_cleanup_array_function, raid_type, nr_data_drives
):
    """The purpose of this test case is to Create 2 array in Write Through mode. Create and mount 256 volume on each array"""
    logger.info(
        " ==================== Test : test_wt_multi_array_256vols ================== "
    )
    try:
        pos = setup_cleanup_array_function
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )

        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
            res = pos.cli.create_array(
                write_buffer=f"uram{str(index)}",
                array_name=array,
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
            )
            assert res[0] == True
            assert pos.cli.mount_array(array_name=array, write_back=False)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=256, size="10gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem" in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=[ss_list[0]]
                )
                == True
            )
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
