import pytest

from pos import POS
import logger
import random
import time


logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict['array']['phase'] = "false"
    data_dict['volume']['phase'] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("no-raid", 1), ("RAID0", 2), ("RAID10", 4), ("RAID10", 2)],
)
def test_wt_multi_array_256vols(raid_type, nr_data_drives):
    """The purpose of this test case is to Create 2 array in Write Through mode. Create and mount 256 volume on each array"""
    logger.info(
        " ==================== Test : test_wt_multi_array_256vols ================== "
    )
    try:
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
