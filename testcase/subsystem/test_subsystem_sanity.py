import pytest
import logger
from pos import POS

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict, data_store
    pos = POS()
    data_store = {}
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "True"
    data_dict['subsystem']["nr_subsystems"] = 64
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    assert pos.cli.reset_devel()[0] == True

    yield pos


def teardown_function():

    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    assert pos.target_utils.get_subsystems_list() == True
    for ss in pos.target_utils.ss_temp_list:
        assert pos.cli.delete_subsystem(nqn_name=ss)[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)
@pytest.mark.sanity
def test_sanitySubsystem():
    try:
        assert pos.target_utils.get_subsystems_list() == True
       
        assert pos.cli.list_array()[0] == True
        for index, array in enumerate(list(pos.cli.array_dict.keys())):
            for i in range(256):
               volname = f'{array}_vol_{str(i)}'
               assert pos.cli.create_volume(array_name=array,volumename= volname,size = "1gb")[0] == True
               assert pos.cli.mount_volume(array_name=array, volumename=volname, nqn= pos.target_utils.ss_temp_list[index])[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.list_volume(array_name=array)[0] == True
            for vol in pos.cli.vols:
                assert pos.cli.unmount_volume(volumename=vol, array_name=array)[0] == True
            
    except Exception as e:
        logger.error(f"TC failed due to {e}")
        assert 0
