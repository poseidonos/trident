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

def test_rebuild_array_state():
    try:
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
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=60",
            )[0]
            == True
        )
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_wb_array_write_nvme_flush_read():
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        assert test_rebuild_array_state() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert pos.client.nvme_flush(dev_list) == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=read --iodepth=64 --direct=1 --numjobs=1 --bs=63k --time_based --runtime=300",
            )[0]
            == True
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_rename_volume_while_io():
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        assert test_rebuild_array_state() == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=read --iodepth=64 --direct=1 --numjobs=1 --bs=63k --time_based --runtime=300",run_async=True
            )[0]
            == True
        )
        assert pos.cli.list_volume(array_name=array_name)
        assert pos.cli.rename_volume(array_name=array_name,volname=pos.cli.vols[0],new_volname='posvol')[0] == True
        logger.info("As expected volume creation failed with special characters")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_unmnt_vol_array_rebuild_states():
    logger.info(
        " ==================== Test : test_unmnt_vol_rebuild_arrray_state ================== "
    )
    try:
        assert test_rebuild_array_state() == True
        assert pos.cli.info_array(array_name=array_name)[0] == True
        remove_drives = [random.choice(pos.cli.array_info[array_name]["data_list"])]
        assert pos.target_utils.device_hot_remove(device_list=remove_drives)
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["situation"])
        if pos.cli.array_info[array_name]["situation"] == "REBUILDING":
            assert pos.cli.unmount_volume(array_name=array_name,volumename=pos.cli.vols[0])[0] == True
        else:
            assert 0
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_rebuild_normal_state():
    logger.info(
        " ==================== Test : test_unmnt_vol_rebuild_arrray_state ================== "
    )
    try:
        assert test_rebuild_array_state() == True
        assert pos.cli.info_array(array_name=array_name)[0] == True
        remove_drives = [random.choice(pos.cli.array_info[array_name]["data_list"])]
        assert pos.target_utils.device_hot_remove(device_list=remove_drives)
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["situation"])
        assert pos.target_utils.array_rebuild_wait(array_name=array_name)
        if pos.cli.array_info[array_name]["situation"] == "REBUILDING":
            assert pos.target_utils.array_rebuild_wait(array_name=array_name)
        else:
            assert 0
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["situation"])
        if pos.cli.array_info[array_name]["situation"] == "NORMAL":
            logger.info("As expected array state change to Normal after rebuild")
        else:
            assert 0

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_array_unmnt_mnt_rebuild_state():
    logger.info(
        " ==================== Test : test_unmnt_vol_rebuild_arrray_state ================== "
    )
    try:
        assert test_rebuild_array_state() == True
        assert pos.cli.info_array(array_name=array_name)[0] == True
        remove_drives = [random.choice(pos.cli.array_info[array_name]["data_list"])]
        assert pos.target_utils.device_hot_remove(device_list=remove_drives)
        time.sleep(60)
        assert pos.cli.info_array(array_name)[0] == True
        array_status = pos.cli.array_info[array_name]
        logger.info(str(array_status))
        logger.info(array_status["situation"])
        if pos.cli.array_info[array_name]["situation"] == "REBUILDING":
            assert pos.cli.unmount_array(array_name=array_name)[0] == False
            assert pos.cli.mount_array(array_name=array_name)[0] == False
        else:
            assert 0
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

