import pytest
import logger

logger = logger.get_logger(__name__)
from common_libs import *


def gc_array_io(pos, fio_user_cmd):
    try:
        global array_name
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.cli.device_list()[0] == True
        data_dict = pos.data_dict
        data_dict["array"]["num_array"] = 1
        data_dict["array"]["pos_array"][0]["raid_type"] = "RAID5"
        data_dict["array"]["pos_array"][0]["data_device"] = 3
        data_dict["array"]["pos_array"][0]["spare_device"] = 1
        data_dict["array"]["pos_array"][0]["write_back"] = "true"
        assert pos.target_utils.bringup_array(data_dict=data_dict) == True
        data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
        assert pos.target_utils.bringup_volume(data_dict=data_dict) == True

        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=30"
        assert run_io(pos, fio_command=fio_cmd) == True
        assert run_io(pos, fio_command=fio_user_cmd) == True

        assert pos.cli.wbt_do_gc(array_name = array_name)[0] == True
        assert pos.cli.wbt_get_gc_status(array_name = array_name)[0] == True
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("bs", [1, 3, 4, 5, 32, 33, 1024, 1023, 1203, 512, 513])
def test_gc_diff_bk_size(array_fixture, bs):
    logger.info(" ==================== Test : test_gc_diff_bk_size ================== ")
    try:
        pos = array_fixture
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs={}k --time_based --runtime=120".format(bs)
        assert gc_array_io(pos, fio_cmd) == True
        logger.info(" ============================= Test ENDs ====================")
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
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=120"
        assert gc_array_io(pos, fio_cmd) == True
        assert pos.cli.volume_list(array_name=array_name)
        assert (
            pos.cli.volume_unmount(array_name=array_name, volumename=pos.cli.vols[0])[0]
            == True
        )
        logger.info(" ============================= Test ENDs ===================")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("mul", [2, 1.5, 0.4, 0.9, 1.9])
def test_gc_diff_io_size(array_fixture, mul):
    logger.info(" ==================== Test : test_gc_diff_io_size ================== ")
    try:
        pos = array_fixture
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --numjobs=1 --bs=64k --size={}gb --direct=1 --time_based --runtime=300".format(int(mul*2000))
        assert gc_array_io(pos, fio_cmd) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_gc_with_rebuild(array_fixture):
    try:
        pos = array_fixture
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=120"
        assert gc_array_io(pos=pos,fio_user_cmd=fio_cmd) == True
        array = list(pos.cli.array_dict.keys())[0]
        assert array_disks_hot_remove(pos=pos, array_name=array, disk_remove_interval_list=[(0,)]) == True
        out, nvme_devs = nvme_connect(pos)
        assert run_fio_all_volumes(pos=pos,fio_cmd=fio_cmd,nvme_devs=nvme_devs) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_gc_with_array_deletion(array_fixture):
    try:
        pos = array_fixture
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=120"
        assert gc_array_io(pos=pos, fio_user_cmd=fio_cmd) == True
        assert array_unmount_and_delete(pos=pos) == True
        assert pos.cli.wbt_do_gc(array_name=array_name)[0] == False
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
