import pytest
import time

import logger
logger = logger.get_logger(__name__)


def gc_array_io(pos):
    try:
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        system_disks = pos.cli.system_disks
        if len(system_disks) < (3):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum 4."
            )
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        assert pos.cli.array_create(array_name=array_name,
                        write_buffer="uram0", data=data_disk_list,
                        spare=[], raid_type="RAID5")[0] == True

        assert pos.cli.array_mount(array_name=array_name, 
                                   write_back=True)[0] == True
        assert pos.cli.volume_create(array_name=array_name,
                    size="2000gb", volumename="vol")[0] == True

        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        ss_list_all = pos.target_utils.ss_temp_list
        ss_list = [ss for ss in ss_list_all if array_name in ss]
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                        volume_list=pos.cli.vols, nqn_list=ss_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=300",
        assert pos.client.nvme_list() == True
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out,
                                        fio_user_data=fio_cmd)[0] == True
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_gc_long_io(array_fixture):
    logger.info(" ==================== Test : test_gc_diff_bk_size ================== ")
    try:
        pos = array_fixture
        assert gc_array_io(pos) == True
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=300",
            )[0]
            == True
        )
        assert pos.cli.wbt_do_gc(array_name = array_name)[0] == True
        assert pos.cli.wbt_get_gc_status(array_name = array_name)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_set_gc_while_io(array_fixture):
    logger.info(" ==================== Test : test_set_gc_while_io ================== ")
    try:
        pos = array_fixture
        assert gc_array_io(pos) == True
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.client.nvme_list() == True
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
def test_gc_in_loop(array_fixture):
    logger.info(" ==================== Test : test_set_gc_while_io ================== ")
    try:
        pos = array_fixture
        assert gc_array_io(pos) == True
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.client.nvme_list() == True
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
