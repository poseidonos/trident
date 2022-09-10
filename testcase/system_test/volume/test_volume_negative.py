import pytest

from pos import POS

import logger
logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict['volume']['phase'] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos

def setup_function():
    data_dict = pos.data_dict
    if pos.target_utils.helper.check_pos_exit() == True:
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

    data_dict['system']['phase'] = "false"
    data_dict['device']['phase'] = "false"
    data_dict['subsystem']['phase'] = "false"
    data_dict['array']['phase'] = "false"

def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.cli.list_array()[0] == True
    for array_name in pos.cli.array_dict.keys():
        assert pos.cli.info_array(array_name=array_name)[0] == True
        if pos.cli.array_dict[array_name].lower() == "mounted":
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            for vol in pos.cli.vols:
                assert pos.cli.info_volume(
                    array_name=array_name, vol_name=vol)[0] == True

                if pos.cli.volume_info[array_name][vol]["status"] == "Mounted":
                    assert pos.cli.unmount_volume(
                        volumename=vol, array_name=array_name)[0] == True
                assert pos.cli.delete_volume(
                    volumename=vol, array_name=array_name)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

@pytest.mark.regression
def test_513_volumes():
    '''The purpose of test is to try to create 513 volumes (256 array 1, 257 array 2) '''
    try:
        logger.info("================ Test: test_513_volumes ================")
        assert pos.cli.list_array()[0] == True
        valid_vols = True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.info_array(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_info[array_name].get("size"))
            vol_size = f"{int(array_size // (1024 * 1024)/ 260)}mb"  # Volume Size in MB
            num_vols = 256
            assert pos.target_utils.create_volume_multiple(array_name, num_vols, size=vol_size) == True
            if not valid_vols:
                vol_name = f"{array_name}_PoS_VoL_257"
                assert pos.cli.create_volume(vol_name, vol_size, array_name)[0] == False
            
            valid_vols = False
        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_257_volumes():
    '''The purpose of test is to try to create 257 and mount volumes on each array '''
    try:
        logger.info("================ Test: test_257_volumes ================")
        assert pos.cli.list_array()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.info_array(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_info[array_name].get("size"))
            vol_size = f"{int(array_size // (1024 * 1024)/ 260)}mb"  # Volume Size in MB
            assert pos.target_utils.create_volume_multiple(array_name, 256, size=vol_size) == True

            assert pos.target_utils.get_subsystems_list() == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
            nqn = ss_list[0]
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            assert pos.target_utils.mount_volume_multiple(array_name, pos.cli.vols, nqn) == True

            # Create and mount 257 volumes
            vol_name = f"{array_name}_Vol_257"
            assert pos.cli.create_volume(vol_name, vol_size, array_name)[0] == False
            # TODO add assert: Due to POS CLI bug assert cann't be verify
            pos.cli.mount_volume(vol_name, array_name, nqn)[0] == False

        logger.info("=============== TEST ENDs ================")
    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)