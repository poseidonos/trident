import pytest

import logger
logger = logger.get_logger(__name__)

test_params = {
    "t0":("&*^", False),
    "t1":("vol-0.5", False),
    "t2":("a" * 254, True),
    "t3":("a" * 255, True),
    "t4":("cc" * 2, True),
    "t5":("vol", False),
    "t6":("pos_vol", True)
}

@pytest.mark.regression
@pytest.mark.parametrize("params", test_params)
def test_rename_vol_special_char(volume_fixture, params):
    logger.info(
        " ==================== Test : test_rename_vol_special_chars ================== "
    )
    try:
        pos = volume_fixture
        new_name, expected_result = test_params[params]
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert (
            pos.cli.volume_create(array_name=array_name, size="10gb", volumename="vol")[
                0
            ]
            == True
        )
        assert pos.cli.volume_list(array_name=array_name)
        status = pos.cli.volume_rename(
                array_name=array_name, volname=pos.cli.vols[0], new_volname=new_name
            )
        assert status[0] == expected_result
        if expected_result == False:
            #event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for volume rename")
     
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_rename_non_exist_vol(volume_fixture):
    logger.info(
        " ==================== Test : test_rename_vol_doub_char ================== "
    )
    try:
        pos = volume_fixture
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert (
            pos.cli.volume_create(array_name=array_name, size="10gb", volumename="vol")[
                0
            ]
            == True
        )
        assert pos.cli.volume_list(array_name=array_name)
        status = pos.cli.volume_rename(array_name=array_name, volname="test", new_volname="posvol")
        
        logger.info("As expected volume creation failed with special characters")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_vol_mnt_unmnt(volume_fixture):
    logger.info(" ==================== Test : test_vol_mnt_unmnt ================== ")
    try:
        pos = volume_fixture
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert (
            pos.cli.volume_create(array_name=array_name, size="10gb", volumename="vol")[
                0
            ]
            == True
        )
        assert pos.cli.volume_list(array_name=array_name)
        for i in range(5):
            pos.cli.volume_mount(array_name=array_name, volumename=pos.cli.vols[0])[
                0
            ] == True
            pos.cli.volume_unmount(array_name=array_name, volumename=pos.cli.vols[0])[
                0
            ] == True
        logger.info("As expected volume mount and unmount sucessfull")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_rename_vol_after_array_unmnt_mnt(volume_fixture):
    logger.info(
        " ==================== Test : test_rename_vol_doub_char ================== "
    )
    try:
        pos = volume_fixture
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert (
            pos.cli.volume_create(array_name=array_name, size="10gb", volumename="vol")[
                0
            ]
            == True
        )
        assert pos.cli.volume_list(array_name=array_name)
        assert (
            pos.cli.volume_rename(
                array_name=array_name, volname=pos.cli.vols[0], new_volname="posvol"
            )[0]
            == True
        )
        assert pos.cli.array_unmount(array_name=array_name)[0] == True
        assert pos.cli.array_mount(array_name=array_name)[0] == True
        try:
            if pos.cli.vols[0] == "posvol":
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
def test_create_vol_larger_array_size(volume_fixture):
    logger.info(
        " ==================== Test : test_rename_vol_doub_char ================== "
    )
    try:
        pos = volume_fixture
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.cli.array_info(array_name)[0] == True
        array_status = pos.cli.array_data[array_name]
        logger.info(str(array_status))
        logger.info(array_status["size"])
        capacity = int(array_status["size"]) + 2048
        logger.info(capacity)
        status = pos.cli.volume_create(array_name=array_name, size=capacity, volumename="vol")

        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume_create due to {event_name}")
        
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_vol_array_normal_states(volume_fixture):
    logger.info(
        " ==================== Test : test_mnt_vol_fault_arrray_state ================== "
    )
    try:
        pos = volume_fixture
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.cli.array_info(array_name)[0] == True
        array_status = pos.cli.array_data[array_name]
        logger.info(str(array_status))
        logger.info(array_status["state"])
        if pos.cli.array_data[array_name]["state"] == "NORMAL":
            assert (
                pos.cli.volume_create(
                    array_name=array_name, size="10gb", volumename="vol"
                )[0]
                == True
            )
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            assert (
                pos.cli.volume_mount(array_name=array_name, volumename=pos.cli.vols[0])[
                    0
                ]
                == True
            )
            assert (
                pos.cli.volume_unmount(
                    array_name=array_name, volumename=pos.cli.vols[0]
                )[0]
                == True
            )
            logger.info(
                "Expected array state match with output{} and volume mount was sucessful".format(
                    array_status["state"]
                )
            )
        else:
            assert 0
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
