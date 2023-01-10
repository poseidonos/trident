import pytest
import pos
from common_libs import *

import logger
logger = logger.get_logger(__name__)


@pytest.mark.sanity
def test_qos_happy_path(array_fixture):
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
    except Exception as e:
        logger.error(e)
        pos.exit_handler()
        assert 0


@pytest.mark.sanity
@pytest.mark.parametrize("num_vol", [1, 256])
def test_qos_set_reset(array_fixture, num_vol):
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = num_vol
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
        assert pos.cli.volume_list(array_name="array1")[0] == True
        for vol in pos.cli.vols:
            assert (
                pos.cli.qos_reset_volume_policy(volumename=vol, arrayname="array1")[0]
                == True
            )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()
        assert 0


@pytest.mark.sanity
def test_qos_rebuilding_Array(array_fixture):
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
        pos.data_dict["array"]["num_array"] = 1
        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)

        assert pos.cli.list_array()[0] == True
        for index, array in enumerate(list(pos.cli.array_dict.keys())):
            assert pos.cli.array_info(array_name=array)[0] == True
            assert (
                pos.target_utils.device_hot_remove(
                    device_list=[pos.cli.array_data[array]["data_list"][0]]
                )
                == True
            )
            assert pos.target_utils.array_rebuild_wait(array_name=array) == True
        assert pos.cli.volume_list(array_name="array1")[0] == True
        for vol in pos.cli.vols:
            assert (
                pos.cli.qos_reset_volume_policy(volumename=vol, arrayname="array1")[0]
                == True
            )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()
        assert 0
