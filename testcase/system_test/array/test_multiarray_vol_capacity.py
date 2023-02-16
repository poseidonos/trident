import pytest

from common_multiarray import *
import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
def test_multi_array_full_cap(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple_with_io(pos, 1, fio_cmd=None) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_full_cap_data_integrity(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        fio_runner = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k --size=100gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert (
            volume_create_and_mount_multiple_with_io(pos, 1, fio_cmd=fio_runner) == True
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_full_cap_max_vols(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple_with_io(pos, 256, fio_cmd=None) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_max_vol_data_integrity(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        fio_runner = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k --size=100gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert (
            volume_create_and_mount_multiple_with_io(pos, 256, fio_cmd=fio_runner)
            == True
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_unmnt_vol(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 1) == True
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.array_unmount(array_name=array_name)[0] == True
        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            if pos.cli.array_dict[array_name].lower() == "unmounted":
                status = pos.cli.volume_mount(array_name=array_name, volumename=pos.cli.vols)
                logger.info("As expected volume mount failed while array is unmounted ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_del_create_array(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 1) == True
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.array_unmount(array_name=array_name)[0] == True
        assert pos.cli.array_delete(array_name=array_name)[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]

        assert pos.cli.array_create(array_name="array3",
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type="RAID5")[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_create_third_array(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 1) == True
        assert pos.cli.array_list()[0] == True
        assert pos.cli.device_create(
            uram_name="uram3", bufer_size=8388608, strip_size=512, numa=1
        )
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(3)]

        status = pos.cli.array_create(array_name="array3",
                    write_buffer="uram3", data=data_disk_list,
                    spare=[], raid_type="RAID5")
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for autoarray create due to {event_name}")
        
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_more_than_max_vols(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        status = volume_create_and_mount_multiple(pos, 257)
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume creation due to {event_name}")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_multi_array_del_vols(array_fixture):
    logger.info(
        " ==================== Test : test_multi_vol_full_cap ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict["array"]["num_array"] = 2
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, 5) == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name in pos.cli.vols:
                assert (
                    pos.cli.volume_unmount(array_name=array_name, volumename=vol_name)[
                        0
                    ]
                    == True
                )
                assert (
                    pos.cli.volume_delete(array_name=array_name, volumename=vol_name)[0]
                    == True
                )
        assert pos.cli.volume_list(array_name=array_name)
        logger.info("As expected No volume listed ")
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
