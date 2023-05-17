import pytest

from common_multiarray import *
import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
def test_multi_create_second_array_with_same_uram(array_fixture):
    logger.info(
        " ==================== Test : test_multi_create_second_array_with_same_uram ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]

        assert pos.cli.array_create(array_name="array2",
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type="RAID5")[0] == False

        logger.info("As expected array creation failed with same uram name ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_array_num_drives(array_fixture):
    logger.info(
        " ==================== Test : test_array_num_drives ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 0
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(10)]

        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type="RAID5")[0] == True

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
def test_unmnt_array_while_io(array_fixture):
    logger.info(
        " ==================== Test : test_unmnt_array_while_io ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple_with_io(pos, 2) == True
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.array_unmount(array_name=array_name)[0] == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_mnt_vol_again(array_fixture):
    logger.info(" ==================== Test : test_mnt_vol_again ================== ")
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
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
def test_unmnt_mnt_for_io(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.target_utils.create_volume_multiple(array_name,
                                    num_vol=1, vol_name="vol") == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True
        assert pos.client.nvme_list(error_recovery=False) == False
        logger.info("As expected no volumes present io due to volume mount")

        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name in pos.cli.vols:
                assert pos.cli.volume_mount(array_name=array_name,
                                        volumename=vol_name)[0] == True

        assert pos.client.nvme_list() == True
        device_list = pos.client.nvme_list_out
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=4k --time_based --runtime=300"

        res, async_out = pos.client.fio_generic_runner(
            device_list, fio_user_data=fio_cmd, run_async=False
        )
        assert res == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0
