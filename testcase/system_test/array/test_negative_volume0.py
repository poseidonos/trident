import pytest

import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression
@pytest.mark.parametrize(
    "new_name,expected_result",[("&*^",False),("vol-0.5",False),('a' * 254,True),('a' * 255,True),('cc' * 2,True),("vol",False),("pos_vol",True)]
)
def test_rename_vol_special_char(setup_cleanup_array_function, new_name,expected_result):
    logger.info(" ==================== Test : test_rename_vol_special_chars ================== ")
    try:
        pos =  setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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
def test_rename_non_exist_vol(setup_cleanup_array_function):
    logger.info(" ==================== Test : test_rename_vol_doub_char ================== ")
    try:
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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
def test_vol_mnt_unmnt(setup_cleanup_array_function):
    logger.info(" ==================== Test : test_vol_mnt_unmnt ================== ")
    try:
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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
def test_rename_vol_after_array_unmnt_mnt(setup_cleanup_array_function):
    logger.info(" ==================== Test : test_rename_vol_doub_char ================== ")
    try:
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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
def test_create_vol_larger_array_size(setup_cleanup_array_function):
    logger.info(" ==================== Test : test_rename_vol_doub_char ================== ")
    try:
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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
def test_vol_array_normal_states(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        pos = setup_cleanup_array_function
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
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


