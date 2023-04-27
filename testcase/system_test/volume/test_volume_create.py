import pytest
import random
import string
import time

import logger
logger = logger.get_logger(__name__)


def generate_volume_name(len_name):
    '''Generate random name of length "len_name"'''

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=len_name))

# Testcase Parameters for test_volume_create

volume_create_tests = {}
volume_create_tests["t0"] = {"volume_name_gen": generate_volume_name(3), "result": True}
volume_create_tests["t1"] = {"volume_name_gen": " ", "result": False}
volume_create_tests["t2"] = {
    "volume_name_gen": generate_volume_name(3) + "  " + generate_volume_name(3),
    "result": True,
}
volume_create_tests["t3"] = {
    "volume_name_gen": generate_volume_name(3) + "  ",
    "result": True,
}
volume_create_tests["t4"] = {
    "volume_name_gen": generate_volume_name(254),
    "result": True,
}
volume_create_tests["t5"] = {
    "volume_name_gen": generate_volume_name(1),
    "result": False,
}
volume_create_tests["t6"] = {"volume_name_gen": generate_volume_name(2), "result": True}
volume_create_tests["t7"] = {
    "volume_name_gen": generate_volume_name(255),
    "result": True,
}

test_list = ["t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7"]
@pytest.mark.regression
@pytest.mark.parametrize("volume_create_test", test_list)
def test_volume_create(volume_fixture, volume_create_test):
    """The purpose of testcase is to create volume with different names"""

    logger.info("================= Test: test_volume_create  =================")
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        vol_name = volume_create_tests[volume_create_test]["volume_name_gen"]
        expected_res = volume_create_tests[volume_create_test]["result"]

        status = pos.cli.volume_create(volumename=vol_name, size="10gb", array_name=array_name)
        assert status[0] == expected_res
        if expected_res == False:
            logger.info(f"Expected failure for volume create")
        
        assert (
            pos.cli.volume_info(array_name=array_name, vol_name=vol_name)[0]
            == expected_res
        )

        if len(vol_name) == 2 or len(vol_name) == 255:
            assert (
                pos.cli.volume_mount(array_name=array_name, volumename=vol_name)[0]
                == True
            )
            assert (
                pos.cli.volume_unmount(array_name=array_name, volumename=vol_name)[0]
                == True
            )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("volnum", [255, 257])
def test_multiple_volume_create(volume_fixture, volnum):
    """The purpose of test is to create multiple volumes"""

    logger.info("================ Test : test_multiple_volume =================")
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        if volnum > 256:
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array_name, num_vol=256, size="10gb"
                )
                == True
            )

            status = pos.cli.volume_create(array_name=array_name, size="10gb", volumename="invalid-vol")
            assert status[0] == False
            event_name = status[1]['output']['Response']['result']['status']['eventName']
            logger.info(f"Expected failure for volume create due to {event_name}")

        else:

            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array_name, num_vol=volnum, size="10gb"
                )
                == True
            )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_duplicate_name(volume_fixture):
    """The purpose is to create volume with duplicate names"""

    logger.info(
        "================ Test : test_volume_create_duplicate_name ================="
    )

    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert (
            pos.cli.volume_create(
                array_name=array_name, size="10gb", volumename="vol-duplicate"
            )[0]
            == True
        )

        status = pos.cli.volume_create(array_name=array_name, size="10gb", volumename="vol-duplicate")
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume create due to {event_name}")

        # Delete the existing volume and retry creating with same name
        assert (
            pos.cli.volume_delete(array_name=array_name, volumename="vol-duplicate")[0]
            == True
        )

        assert (
            pos.cli.volume_create(
                array_name=array_name, size="10gb", volumename="vol-duplicate"
            )[0]
            == True
        )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_lt_aligned_blocksize(volume_fixture):
    """The purpose of test is to create volume less than aligned block size"""

    logger.info(
        "================ Test : test_volume_create_size_lt_aligned ================="
    )
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        # 1MB = 1024 * 1024 Bytes
        # Less than 1MB => Unaligned blocksize
        status = pos.cli.volume_create(array_name=array_name, size="1024B", volumename="invalid-vol")
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume create due to {event_name}")

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_gt_max_array_capacity(volume_fixture):
    """The purpose of test is to create volume exceeding max array capacity"""

    logger.info(
        "================ Test : test_volume_gt_array_capacity ================="
    )
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        num_vol = 255
        assert pos.cli.array_info(array_name=array_name)[0] == True
        array_size = int(pos.cli.array_data[array_name].get("size"))
        vol_size = f"{int((array_size // num_vol) // (1024 * 1024))}mb"
        assert (
            pos.target_utils.create_volume_multiple(
                array_name=array_name, num_vol=255, size=vol_size
            )
            == True
        )

        # 255 Volumes used up the Max array Capacity
        # Creating 256th Volume with exceeded array capacity

        status = pos.cli.volume_create(array_name=array_name, size="10gb", volumename="invalid-vol")
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume create due to {event_name}")

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array_create_with_invalid_uram(array_fixture):
    """The pupose of testcase is to create an array with invalid uram"""

    logger.info(
        "================ Test : test_array_create_with_invalid_uram ================="
    )
    try:
        pos = array_fixture
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(4)]

        status = pos.cli.array_create(array_name="invalid_array",
                        write_buffer="uram-invalid", data=data_disk_list, 
                        spare=[], raid_type="RAID5")
        assert status[0] == False
        #event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info("Expected failure for array create with invalid uram")
        
        logger.info("=============== TEST ENDs ================")
    except Exception as e:
        logger.info(f"Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_without_array_mount(volume_fixture):
    """The purpose of test is to create a volume on unmounted array"""

    logger.info(
        "================ Test : test_volume_create_without_array_mount ================="
    )
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        # unmount the array
        assert (
            pos.cli.array_unmount(
                array_name=array_name,
            )[0]
            == True
        )

        status = pos.cli.volume_create(array_name=array_name, size="10gb", volumename="invalid-vol")
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume create due to {event_name}")
        
        # mount the array
        assert (
            pos.cli.array_mount(
                array_name=array_name,
            )[0]
            == True
        )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0


@pytest.mark.regression
def test_multiple_volume_create_delete_with_io(volume_fixture):
    """The purpose of test is to create and delete volume in loop.
    Run IO on the active volumes with data integrity check.'
    """
    logger.info(
        "================ Test : test_multiple_volume_create_delete_with_io ================="
    )
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        pos.target_utils.get_subsystems_list()
        assert (
            pos.target_utils.create_volume_multiple(
                array_name=array_name, num_vol=15, size="1gb"
            )
            == True
        )

        assert pos.cli.volume_list(array_name=array_name)[0] == True
        volume_list = pos.cli.vols

        assert pos.target_utils.mount_volume_multiple(
                        array_name, volume_list=volume_list,
                        nqn=pos.target_utils.ss_temp_list[0]) == True

        for _ in range(12):
            assert pos.cli.volume_unmount(array_name=array_name,
                                volumename=volume_list[_])[0] == True
            assert pos.cli.volume_delete(array_name=array_name,
                                volumename=volume_list[_])[0] == True

        assert pos.target_utils.create_volume_multiple(array_name=array_name,
                                            num_vol=3, size="1gb") == True

        assert pos.cli.volume_list(array_name=array_name)[0] == True
        volume_list = pos.cli.vols
        for vol in volume_list:
            assert pos.cli.volume_info(array_name=array_name, vol_name=vol)
            if pos.cli.volume_data[array_name][vol]["status"] == "Unmounted":
                assert (
                    pos.cli.volume_mount(
                        array_name=array_name,
                        volumename=vol,
                        nqn=pos.target_utils.ss_temp_list[0],
                    )[0]
                    == True
                )

        assert (
            pos.client.nvme_connect(
                pos.target_utils.ss_temp_list[0],
                pos.target_utils.helper.ip_addr[0],
                "1158",
            )
            == True
        )

        assert pos.client.nvme_list() == True
        pos.client.check_system_memory()

        nvme_devs = pos.client.nvme_list_out

        fio_cmd = f"fio --name=sequential_write --runtime=300 --ramp_time=60  --ioengine=libaio  --iodepth=16 --rw=write --size=5g --bs=4kb --direct=1 --offset=0 --verify=crc32c"

        block_io_devs = nvme_devs
        io_mode = True  # Block IO
        out, async_block_io = pos.client.fio_generic_runner(
            block_io_devs, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
        )
        assert out == True

        # Wait for async FIO completions
        while True:
            time.sleep(30)  # Wait for 30 seconds
            block_io = async_block_io.is_complete()

            msg = []
            if not block_io:
                msg.append("Block IO")

            if msg:
                logger.info(
                    "'{}' is still running. Wait 30 seconds...".format(",".join(msg))
                )
                continue
            break

        pos.client.check_system_memory()

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_unmount_volume(volume_fixture):
    """The purpose of test is to unmount the volume from target"""

    logger.info("================ Test : test_unmount_volume =================")
    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert (
            pos.cli.volume_create(
                volumename="vol_1", size="10gb", array_name=array_name
            )[0]
            == True
        )
        assert (
            pos.cli.volume_info(array_name=array_name, vol_name="vol_1")[0]
            == True
        )

        assert (
            pos.cli.volume_mount(array_name=array_name, volumename="vol_1")[0]
            == True
        )
        assert pos.cli.subsystem_list()[0] == True

        assert (
            pos.cli.volume_unmount(array_name=array_name, volumename="vol_1")[
                0
            ]
            == True
        )

        assert pos.cli.subsystem_list()[0] == True

        # Unmounting & Deleting the Array
        assert pos.cli.array_unmount(array_name=array_name)[0] == True
        assert pos.cli.array_delete(array_name=array_name)[0] == True

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_unmount_volume_connected(volume_fixture):
    """The purpose of test is to unmount the connected volume from target"""

    logger.info(
        "================ Test : test_unmount_volume_connected ================="
    )

    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert (
            pos.cli.volume_create(
                array_name=array_name, size="10gb", volumename="vol1"
            )[0]
            == True
        )

        assert pos.cli.volume_info(array_name=array_name, vol_name="vol1")[0] == True
        assert pos.target_utils.get_subsystems_list() == True

        assert (
            pos.cli.volume_mount(
                array_name=array_name,
                volumename="vol1",
                nqn=pos.target_utils.ss_temp_list[0],
            )[0]
            == True
        )

        assert (
            pos.client.nvme_connect(
                pos.target_utils.ss_temp_list[0],
                pos.target_utils.helper.ip_addr[0],
                "1158",
            )
            == True
        )

        assert pos.client.nvme_list() == True
        # Unmounting the connected Volume
        status = pos.cli.volume_unmount(array_name=array_name, volumename="vol1")
        assert status[0] == True
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume unmount due to {event_name}")

        assert (
            pos.client.nvme_disconnect(nqn=[pos.target_utils.ss_temp_list[0]]) == True
        )
        assert (
            pos.cli.volume_unmount(array_name=array_name, volumename="vol1")[0] == False
        )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_mount_invalid_name(volume_fixture):
    """The purpose of test is to mount a volume with non-existing volume name"""

    logger.info(
        "================ Test : test_volume_mount_invalid_name ================="
    )

    try:
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        status = pos.cli.volume_mount(array_name=array_name, volumename="non_existing_vol")

        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for volume mount due to {event_name}")

    except Exception as e:
        logger.info(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
