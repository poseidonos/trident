import pytest
#from lib.pos import POS
import logger
from pos import POS
logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos
    pos = POS()
    data_store = {}
    data_dict = pos.data_dict
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos
    
def teardown_function():

    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True
        # assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)
@pytest.mark.sanity   
def test_do_gc_emptyarray():
    try:
        """GC is expected to fail on 100% Free array """
        assert pos.cli.wbt_do_gc()[0] == False
    except Exception as e:
        logger.error(e)
        pos.exit_handler()
@pytest.mark.sanity
def test_gcMaxvol():
    """Trigger garbage collection with longevity of I/O"""
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_array()[0] == True
        for index,array in enumerate(list(pos.cli.array_dict.keys())):
            assert pos.target_utils.deleteAllVolumes(arrayname=array) == True
            assert pos.target_utils.create_volume_multiple(array_name=array, num_vol=256) == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            assert pos.target_utils.mount_volume_multiple(array_name=array, volume_list=pos.cli.vols, nqn_list = pos.target_utils.ss_temp_list[index]) == True
            assert pos.client.nvme_connect(pos.target_utils.ss_temp_list[index], pos.target_utils.helper.ip_addr[0], "1158") ==True
        assert pos.client.nvme_list() == True
        assert (pos.client.fio_generic_runner(pos.client.nvme_list_out,fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10")[0] == True)
        assert pos.cli.wbt_do_gc()[0] == False
        assert pos.cli.wbt_get_gc_status()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.target_utils.deleteAllVolumes(arrayname=array) == True
            
        logger.info(
            " ============================= Test ENDs ======================================"
        )
        
                                
    except Exception as e:
        logger.error(e)
        pos.exit_handler()
