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
    data_dict['array']['num_array'] = 0
    data_dict['volume']['phase'] = "false"
    #array_name = data_dict["array"]["pos_array"][0]["array_name"]
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
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

def gc_array_io():
    try:
        global array_name
        array_name="POSARRAY1"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (3):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        #spare_disk_list = [system_disks.pop()]

        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert pos.cli.create_volume(array_name=array_name, size="2000gb", volumename="vol")[0]== True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem1" in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

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
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("bs", [1, 3, 4, 5, 32, 33, 1024, 1023, 1203, 512, 513], )
def test_gc_diff_bk_size(bs):
    logger.info(
        " ==================== Test : test_gc_diff_bk_size ================== "
    )
    try:
        assert gc_array_io() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs={}k --time_based --runtime=120".format(bs)
            )[0]
            == True
        )
        assert pos.cli.wbt_do_gc()[0] == True
        assert pos.cli.wbt_get_gc_status()[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_gc_after_unmnt_vol():
    logger.info(
        " ==================== Test : test_gc_after_unmnt_vol ================== "
    )
    try:
        assert gc_array_io() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=120",
            )[0]
            == True
        )
        assert pos.cli.wbt_do_gc()[0] == True
        assert pos.cli.wbt_get_gc_status()[0] == True
        assert pos.cli.list_volume(array_name=array_name)
        assert pos.cli.unmount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0]== True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
@pytest.mark.parametrize("mul", [2,1.5,0.4,0.9,1.9])
def test_gc_diff_io_size(mul):
    logger.info(
        " ==================== Test : test_gc_diff_io_size ================== "
    )
    try:
        assert gc_array_io() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --numjobs=1 --bs=64k --size={}gb --direct=1 --time_based --runtime=300".format(int(mul*2000))
            )[0]
            == True
        )
        assert pos.cli.wbt_do_gc()[0] == True
        assert pos.cli.wbt_get_gc_status()[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


