import pytest
from pos import POS
import logger
logger = logger.get_logger(__name__)
from common_libs import *

def gc_array_io(pos):
    try:
        global array_name
        array_name=pos.data_dict['array']['pos_array'][0]["array_name"]
        assert pos.cli.list_device()[0] == True
        data_dict = pos.data_dict
        data_dict['array']['num_array'] = 1
        data_dict['array']['pos_array'][0]["data_device"] = 3
        data_dict['array']['pos_array'][0]["spare_device"] = 1
        data_dict['array']['pos_array'][0]["write_back"] = "true"
        assert pos.target_utils.bringupArray(data_dict = data_dict) == True
        data_dict['volume']['pos_volumes'][0]['num_vol'] = 1
        assert pos.target_utils.bringupVolume(data_dict = data_dict) == True
        assert run_io(pos, fio_command="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=30")
        assert pos.target_utils.get_subsystems_list() == True
        
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=read --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=30",
            )[0]
            == True
        )
        logger.info("GC will fail as 100% IO is not written")
        pos.cli.wbt_do_gc()
        pos.cli.wbt_get_gc_status()[0]
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
@pytest.mark.parametrize("bs", [1, 3, 4, 5, 32, 33, 1024, 1023, 1203, 512, 513] )
def test_gc_diff_bk_size(array_fixture,bs):
    logger.info(
        " ==================== Test : test_gc_diff_bk_size ================== "
    )
    try:
        pos = array_fixture
        assert gc_array_io(pos) == True
        logger.info(
            " ============================= Test ENDs ===================="
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)



@pytest.mark.regression
def test_gc_after_unmnt_vol(array_fixture):
    logger.info(
        " ==================== Test : test_gc_after_unmnt_vol ================== "
    )
    try:
        pos = array_fixture
        assert gc_array_io(pos) == True
        
        assert pos.cli.list_volume(array_name=array_name)
        assert pos.cli.unmount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
        logger.info(
            " ============================= Test ENDs ==================="
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
@pytest.mark.parametrize("mul", [2,1.5,0.4,0.9,1.9])
def test_gc_diff_io_size(array_fixture,mul):
    logger.info(
        " ==================== Test : test_gc_diff_io_size ================== "
    )
    try:
        pos = array_fixture
        assert gc_array_io(pos) == True
        
        logger.info(
            " ============================= Test ENDs ======================================"        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
