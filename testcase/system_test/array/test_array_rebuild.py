import pytest
from pos import POS
import logger
logger = logger.get_logger(__name__)
from common_libs import *
import random
import time
def rebuild_array_state(pos):
    try:
        global array_name
        pos.data_dict['array']['num_array'] = 1
        assert pos.target_utils.bringupArray(data_dict = pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict = pos.data_dict) == True
        assert pos.cli.list_array()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.target_utils.get_subsystems_list() == True
        run_io(pos)
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
def drive_detach(pos):
    assert pos.cli.info_array(array_name=array_name)[0] == True
    remove_drives = [random.choice(pos.cli.array_info[array_name]["data_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives)
    assert pos.cli.info_array(array_name)[0] == True
@pytest.mark.regression
def test_wb_array_write_nvme_flush_read(array_fixture):
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        pos = array_fixture
        assert rebuild_array_state(pos) == True
        run_io(pos)
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_rename_volume_while_io(array_fixture):
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        pos = array_fixture
        assert rebuild_array_state(pos) == True
        run_io(pos)
        assert pos.cli.list_volume(array_name=array_name)
        assert pos.cli.rename_volume(array_name=array_name,volname=pos.cli.vols[0],new_volname='posvol')[0] == True
        logger.info("As expected volume creation failed with special characters")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array_rebuild_normal_state(array_fixture):
    logger.info(
        " ==================== Test : test_unmnt_vol_rebuild_arrray_state ================== "
    )
    try:
        pos = array_fixture
        assert rebuild_array_state(pos) == True
        drive_detach(pos)
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["situation"])
        assert pos.target_utils.array_rebuild_wait(array_name=array_name)
        if pos.cli.array_info[array_name]["situation"] == "REBUILDING":
            assert pos.target_utils.array_rebuild_wait(array_name=array_name)
        else:
            assert 0
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["situation"])
        if pos.cli.array_info[array_name]["situation"] == "NORMAL":
            logger.info("As expected array state change to Normal after rebuild")
        else:
            assert 0

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_unmnt_mnt_rebuild_state(array_fixture):
    logger.info(
        " ==================== Test : test_unmnt_vol_rebuild_arrray_state ================== "
    )
    try:
        pos = array_fixture
        assert rebuild_array_state(pos) == True
        drive_detach(pos)
        time.sleep(60)
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        if pos.cli.array_info[array_name]["situation"] == "REBUILDING":
            assert pos.cli.unmount_array(array_name=array_name)[0] == False
            assert pos.cli.mount_array(array_name=array_name)[0] == False
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

