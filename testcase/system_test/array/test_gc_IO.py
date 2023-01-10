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
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.array_list()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.array_unmount(array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


def gc_array_io():
    try:
        global array_name
        array_name = data_dict["array"]["pos_array"][0]["array_name"]
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.devel_resetmbr()[0] == True
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (3):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        assert (
            pos.cli.array_create(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.array_mount(array_name=array_name, write_back=True)[0] == True
        assert (
            pos.cli.volume_create(
                array_name=array_name, size="2000gb", volumename="vol"
            )[0]
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
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
def test_gc_long_io():
    logger.info(" ==================== Test : test_gc_diff_bk_size ================== ")
    try:
        assert gc_array_io() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=300",
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
def test_set_gc_while_io():
    logger.info(" ==================== Test : test_set_gc_while_io ================== ")
    try:
        assert gc_array_io() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        res, async_out = pos.client.fio_generic_runner(
            pos.client.nvme_list_out,
            fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=read --iodepth=64 --direct=1 --numjobs=1 --bs=63k --time_based --runtime=300",
            run_async=True,
        )
        assert res == True
        assert (
            pos.cli.wbt_set_gc_threshold(array_name=array_name, normal=10, urgent=3)[0]
            == True
        )
        assert pos.cli.wbt_get_gc_status(array_name=array_name)[0] == True

        # Wait for async FIO completions
        while async_out.is_complete() == False:
            logger.info("FIO is still running. Wait 30 seconds...")
            time.sleep(30)
        logger.info("As expected gc set while io is running")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_gc_in_loop():
    logger.info(" ==================== Test : test_set_gc_while_io ================== ")
    try:
        assert gc_array_io() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=read --iodepth=64 --direct=1 --numjobs=1 --bs=63k --time_based --runtime=300",
                run_async=True,
            )[0]
            == True
        )
        for i in range(10):
            assert (
                pos.cli.wbt_set_gc_threshold(
                    array_name=array_name, normal=10, urgent=3
                )[0]
                == True
            )
            assert pos.cli.wbt_get_gc_status(array_name=array_name)[0] == True
        logger.info("As expected gc is running fine")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
