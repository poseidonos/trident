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
def test_multi_create_second_array_with_same_uram(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_create_second_array_with_same_uram ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        spare_disk_list = []
        assert (
            pos.cli.array_create(
                write_buffer="uram0",
                data=data_disk_list,
                spare=spare_disk_list,
                raid_type="RAID5",
                array_name="array2",
            )[0]
            == False
        )
        logger.info("As expected array creation failed with same uram name ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_array_num_drives(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_array_num_drives ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 0
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(10)]
        spare_disk_list = []
        assert (
            pos.cli.array_create(
                write_buffer="uram0",
                data=data_disk_list,
                spare=spare_disk_list,
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.array_mount(array_name=array_name)[0] == True
        assert volume_create_and_mount_multiple(pos, 1) == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_unmnt_array_while_io(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_unmnt_array_while_io ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple_with_io(pos, 2) == True
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.array_unmount(array_name=array_name)[0] == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_mnt_vol_again(setup_cleanup_array_function):
    logger.info(" ==================== Test : test_mnt_vol_again ================== ")
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 2) == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name in pos.cli.vols:
                assert (
                    pos.cli.volume_mount(array_name=array_name, volumename=vol_name)[0]
                    == False
                )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_unmnt_mnt_for_io(setup_cleanup_array_function):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = setup_cleanup_array_function
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array_name, num_vol=1, vol_name="vol"
                )
                == True
            )
        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True
        assert pos.client.nvme_list() == False
        logger.info("As expected no volumes present io due to volume mount")
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name in pos.cli.vols:
                assert (
                    pos.cli.volume_mount(array_name=array_name, volumename=vol_name)[0]
                    == True
                )

        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True
        assert pos.client.nvme_list() == True
        device_list = pos.client.nvme_list_out
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=4k --time_based --runtime=300"
        fio_user_data = fio_cmd

        res, async_out = pos.client.fio_generic_runner(
            device_list, fio_user_data=fio_cmd, run_async=False
        )
        assert res == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0
