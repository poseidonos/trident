import pytest
import traceback

from pos import POS
import random
import time
import pprint

from common_multiarray import *
import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression
def test_multi_array_full_cap(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple_with_io(pos ,1,fio_cmd=None) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multi_array_full_cap_data_integrity(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        fio_runner="fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k --size=100gb --do_verify=1 --verify=pattern --verify_pattern=0x5678 --time_based --runtime=300"
        assert volume_create_and_mount_multiple_with_io(pos ,1,fio_cmd=fio_runner) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multi_array_full_cap_max_vols(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple_with_io(pos ,256,fio_cmd=None) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multi_array_max_vol_data_integrity(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        fio_runner="fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k --size=100gb --do_verify=1 --verify=pattern --verify_pattern=0x5678 --time_based --runtime=300"
        assert volume_create_and_mount_multiple_with_io(pos ,256,fio_cmd=fio_runner) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multi_array_unmnt_vol(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 1) == True
        assert pos.cli.list_array()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.list_array()[0] == True
        for array_name in pos.cli.array_dict.keys():
            if  pos.cli.array_dict[array_name].lower() == "unmounted":
                assert pos.cli.mount_volume(array_name=array_name,volumename=pos.cli.vols)[0] == False
                logger.info("As expected volume mount failed while array is unmounted ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multi_array_del_create_array(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 1) == True
        assert pos.cli.list_array()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.delete_array(array_name=array_name)[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        spare_disk_list = []
        assert (pos.cli.create_array(write_buffer="uram0",data=data_disk_list,spare=spare_disk_list,raid_type='RAID5',array_name='array3',
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
def test_multi_array_create_third_array(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 1) == True
        assert pos.cli.list_array()[0] == True
        assert pos.cli.create_device(uram_name='uram3',bufer_size=8388608,strip_size=512,numa=1)
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        spare_disk_list = []
        assert (pos.cli.create_array(write_buffer="uram3",data=data_disk_list,spare=spare_disk_list,raid_type='RAID5',array_name='array3',
            )[0]
            == False
        )
        logger.info("As expected array creation exceeded the limit ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multi_array_more_than_max_vols(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos ,257) == False
        logger.info("As expected volume creation exceeded the limit and capacity ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
def test_multi_array_del_vols(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 5) == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.list_volume(array_name=array_name)[0] == True
            for vol_name in pos.cli.vols:
                assert pos.cli.unmount_volume(array_name=array_name,volumename=vol_name)[0] == True
                assert pos.cli.delete_volume(array_name=array_name,volumename=vol_name)[0]== True
        assert pos.cli.list_volume(array_name=array_name)
        logger.info("As expected No volume listed ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

