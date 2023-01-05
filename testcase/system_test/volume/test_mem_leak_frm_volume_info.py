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

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["array"]["num_array"] = 1
    data_dict["volume"]["phase"] = "false"
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
            assert pos.cli.volume_list(array_name=array)[0] == True
            if len(pos.cli.vols) > 0:
                for vol in pos.cli.vols:
                    assert pos.cli.volume_info(array_name=array,vol_name=vol)[0] == True
                    if pos.cli.volume_info[array][vol]["status"].lower() == "mounted":
                        assert pos.cli.volume_unmount(volumename=vol,array_name=array)[0] == True
                        assert pos.cli.volume_delete(volumename=vol,array_name=array)[0] == True
                    else:
                        assert pos.cli.volume_delete(volumename=vol,array_name=array)[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

def test_mem_leak_from_volume_info():
    assert pos.cli.list_array()[0] == True
    array = list(pos.cli.array_dict.keys())[0]
    assert pos.target_utils.create_volume_multiple(array_name=array,vol_name='vol',num_vol=256,size='1gb') == True
    assert pos.cli.volume_list(array_name=array)[0] == True
    assert pos.target_utils.get_subsystems_list() == True
    assert pos.target_utils.mount_volume_multiple(array_name=array,volume_list=[pos.cli.vols],nqn_list=[pos.target_utils.ss_temp_list]) == True
    assert pos.cli.volume_list()[0] == True
    for i in range(3):
        for vol in pos.cli.vols:
            assert pos.cli.volume_info(array_name=array,vol_name=vol)[0] == True
            assert pos.target_utils.helper.check_system_memory() == True
        logger.info(f"Memory Info: {pos.target_utils.helper.sys_memory_list}")

def test_alternative_volume_info():
    assert pos.cli.list_array()[0] == True
    array = list(pos.cli.array_dict.keys())[0]
    volume_name = array+'vol'
    assert pos.cli.volume_create(array_name=array,volumename=volume_name,size='1gb')[0] == True
    assert pos.cli.volume_mount(array_name=array,volumename=volume_name)[0] == True
    for i in range(3):
        assert pos.cli.volume_info(array_name=array,vol_name=volume_name)[0] == True
        assert pos.cli.volume_info[array][volume_name]["status"].lower() == "mounted"
        assert pos.cli.volume_unmount(array_name=array,volumename=volume_name)[0] == True
        assert pos.cli.volume_info(array_name=array,vol_name=volume_name)[0] == True
        assert pos.cli.volume_info[array][volume_name]["status"].lower() == "unmounted"
        assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.volume_mount(array_name=array,volumename=volume_name)[0] == True
        assert pos.cli.volume_info(array_name=array, vol_name=volume_name)[0] == True
        if pos.cli.volume_info[array][volume_name]["status"].lower() == "mounted":
            assert pos.cli.volume_unmount(volumename=volume_name,array_name=array)[0] == True
            assert pos.cli.volume_mount(volumename=volume_name,array_name=array)[0] == True
        assert pos.cli.volume_info(array_name=array, vol_name=volume_name)[0] == True
        assert pos.cli.volume_info[array][volume_name]["status"].lower() == "mounted"