import pytest
import traceback

from pos import POS
import logger
import random
import time
import pprint

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict , array_name
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict['array']['num_array'] = 1
    data_dict['volume']['phase'] = "false"
    array_name = data_dict["array"]["pos_array"][0]["array_name"]
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos

def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")

    assert pos.cli.list_volume(array_name=array_name)[0] == True
    for vol_name in pos.cli.vols:
        assert pos.cli.delete_volume(vol_name, array_name)[0] == True
            
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
@pytest.mark.parametrize(
    "new_name,expected_result",[("&*^",False),("vol-0.5",False),('a' * 254,True),('a' * 255,True),('cc' * 2,True),("vol",False),("pos_vol",True)]
)
def test_rename_vol_special_char(new_name,expected_result):
    logger.info(" ==================== Test : test_rename_vol_special_chars ================== ")
    try:
        assert pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[0]== True
        assert pos.cli.list_volume(array_name=array_name)
        assert pos.cli.rename_volume(array_name=array_name,volname=pos.cli.vols[0],new_volname=new_name)[0] == expected_result
        logger.info("As expected volume creation failed with special characters")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_rename_non_exist_vol():
    logger.info(" ==================== Test : test_rename_vol_doub_char ================== ")
    try:
        assert pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[0]== True
        assert pos.cli.list_volume(array_name=array_name)
        assert pos.cli.rename_volume(array_name=array_name,volname='test',new_volname='posvol')[0] == False
        logger.info("As expected volume creation failed with special characters")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_vol_mnt_unmnt():
    logger.info(" ==================== Test : test_vol_mnt_unmnt ================== ")
    try:
        assert pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[0]== True
        assert pos.cli.list_volume(array_name=array_name)
        for i in range(5):
            pos.cli.mount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
            pos.cli.unmount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
        logger.info("As expected volume mount and unmount sucessfull")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_rename_vol_after_array_unmnt_mnt():
    logger.info(" ==================== Test : test_rename_vol_doub_char ================== ")
    try:
        assert pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[0]== True
        assert pos.cli.list_volume(array_name=array_name)
        assert pos.cli.rename_volume(array_name=array_name,volname=pos.cli.vols[0],new_volname='posvol')[0] == True
        assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.mount_array(array_name=array_name)[0] == True
        try:
            if pos.cli.vols[0] == 'posvol':
                logger.info("As expected newname matched after array mnt and unmnt")
        except Exception as e:
            logger.error(f"Test script failed due to {e}")
            
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)



@pytest.mark.regression
def test_create_vol_larger_array_size():
    logger.info(" ==================== Test : test_rename_vol_doub_char ================== ")
    try:
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["size"])
        capacity = int(array_status["size"])+2048
        logger.info(capacity)
        assert pos.cli.create_volume(array_name=array_name, size=capacity, volumename="vol")[0]== False
        logger.info("As expected volume creation failed with huge volume size than array size")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_vol_array_normal_states():
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_info[array_name]["state"] == "NORMAL":
            assert pos.cli.create_volume(array_name=array_name, size="10gb", volumename="vol")[0]== True
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            assert pos.cli.mount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
            assert pos.cli.unmount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
            logger.info("Expected array state match with output{} and volume mount was sucessful".format(array_status["state"]))
        else:
            assert 0
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


