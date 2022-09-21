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

def test_gc_vol_create_delete():
    logger.info(" ==================== Test : test_gc_vol_create_delete ================== ")
    try:
        assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array_name, num_vol=4, size="500GB"
                )
                == True
            )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert (pos.target_utils.mount_volume_multiple(array_name=array_name,volume_list=pos.cli.vols,nqn_list=ss_list,
                )
                == True
            )
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        assert pos.cli.unmount_volume(array_name=array_name,volumename=pos.cli.vols[-1])[0]== True
        assert pos.cli.delete_volume(volumename=pos.cli.vols[-1], array_name=array_name)[0] == True
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=300",
            )[0]
            == True
        )
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=300",
            )[0]
            == True
        )
        assert pos.cli.wbt_do_gc()[0] == True
        assert pos.cli.wbt_get_gc_status()[0] == True
        return True
        logger.info(
            " ============================= Test ENDs ======================================"
            )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

