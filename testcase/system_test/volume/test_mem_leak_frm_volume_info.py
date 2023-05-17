import pytest

import logger
logger = logger.get_logger(__name__)

def test_mem_leak_from_volume_info(volume_fixture):
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array = list(pos.cli.array_dict.keys())[0]
        assert pos.target_utils.create_volume_multiple(array_name=array,
                                                       vol_name='vol', 
                                                       num_vol=256,size='1gb'
                                                       ) == True
        assert pos.cli.volume_list(array_name=array)[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        nqn = pos.target_utils.ss_temp_list[0]
        assert pos.target_utils.mount_volume_multiple(array_name=array,
                                                      volume_list=pos.cli.vols,
                                                      nqn=nqn) == True
        assert pos.cli.volume_list(array_name=array)[0] == True
        for i in range(3):
            for vol in pos.cli.vols:
                assert pos.cli.volume_info(array_name=array,vol_name=vol)[0] == True
                assert pos.target_utils.helper.check_system_memory() == True
            logger.info(f"Memory Info: {pos.target_utils.helper.sys_memory_list}")
    except Exception as e:
        logger.error(f"Test Failed due to {e}")
        pos.exit_handler(expected=False)

def test_alternative_volume_info(volume_fixture):
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array = list(pos.cli.array_dict.keys())[0]
        volume_name = array+'vol'
        assert pos.cli.volume_create(array_name=array,volumename=volume_name,size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array,volumename=volume_name)[0] == True
        for i in range(3):
            assert pos.cli.volume_info(array_name=array,vol_name=volume_name)[0] == True
            assert pos.cli.volume_data[array][volume_name]["status"].lower() == "mounted"
            assert pos.cli.volume_unmount(array_name=array,volumename=volume_name)[0] == True
            assert pos.cli.volume_info(array_name=array,vol_name=volume_name)[0] == True
            assert pos.cli.volume_data[array][volume_name]["status"].lower() == "unmounted"
            assert pos.cli.array_unmount(array_name=array)[0] == True
            assert pos.cli.array_mount(array_name=array)[0] == True
            assert pos.cli.volume_mount(array_name=array,volumename=volume_name)[0] == True
            assert pos.cli.volume_info(array_name=array, vol_name=volume_name)[0] == True
            if pos.cli.volume_data[array][volume_name]["status"].lower() == "mounted":
                assert pos.cli.volume_unmount(volumename=volume_name,array_name=array)[0] == True
                assert pos.cli.volume_mount(volumename=volume_name,array_name=array)[0] == True
            assert pos.cli.volume_info(array_name=array, vol_name=volume_name)[0] == True
            assert pos.cli.volume_data[array][volume_name]["status"].lower() == "mounted"
    except Exception as e:
        logger.error(f"Test Failed due to {e}")
        pos.exit_handler(expected=False)