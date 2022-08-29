import pytest
import logger
import random
import string

from pos import POS

logger = logger.get_logger(__name__)


def generate_volume_name(len_name):
    ''' Generate random name of length "len_name" '''

    return ''.join(random.choices(string.ascii_lowercase +
                                  string.digits, k=len_name))


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, array_name, nr_data_drives
    pos = POS("pos_config.json")
    data_dict = pos.data_dict

    data_dict['array']['num_array'] = 1
    data_dict['volume']['phase'] = "false"
    data_dict['subsystem']['pos_subsystems'][0]['nr_subsystems'] = 1
    data_dict['subsystem']['pos_subsystems'][1]['nr_subsystems'] = 0
    array_name = data_dict["array"]["pos_array"][0]["array_name"]
    nr_data_drives = data_dict["array"]["pos_array"][0]["data_device"]

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
                assert pos.cli.list_volume(array_name=array)[0] == True
                for vol in pos.cli.vols:
                    assert pos.cli.info_volume(
                        array_name=array, vol_name=vol)[0] == True

                    if pos.cli.volume_info[array_name][vol]["status"] == "Mounted":
                        assert pos.cli.unmount_volume(
                            volumename=vol, array_name=array)[0] == True
                    assert pos.cli.delete_volume(
                        volumename=vol, array_name=array)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


# Testcase Parameters for test_volume_create

volume_create_tests = {}
volume_create_tests["t0"] = {
    "volume_name_gen": generate_volume_name(3), "result": True}
volume_create_tests["t1"] = {
    "volume_name_gen": generate_volume_name(0), "result": False}
volume_create_tests["t2"] = {"volume_name_gen": generate_volume_name(
    3)+"  "+generate_volume_name(3), "result": True}
volume_create_tests["t3"] = {
    "volume_name_gen": generate_volume_name(3)+"  ", "result": True}
volume_create_tests["t4"] = {
    "volume_name_gen": generate_volume_name(254), "result": True}
volume_create_tests["t5"] = {
    "volume_name_gen": generate_volume_name(1), "result": False}
volume_create_tests["t6"] = {
    "volume_name_gen": generate_volume_name(2), "result": True}
volume_create_tests["t7"] = {
    "volume_name_gen": generate_volume_name(255), "result": True}

test_list = ["t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7"]


@pytest.mark.regression
@pytest.mark.parametrize("volume_create_test", test_list)
def test_volume_create(volume_create_test):
    '''The purpose of testcase is to create volume with different names'''

    logger.info("================= Test: test_volume_create  =================")

    try:
        vol_name = volume_create_tests[volume_create_test]["volume_name_gen"]
        expected_res = volume_create_tests[volume_create_test]["result"]

        assert pos.cli.create_volume(
            volumename=vol_name, size="10gb", array_name=array_name)[0] == expected_res
        assert pos.cli.info_volume(array_name=array_name, vol_name=vol_name)[
            0] == expected_res

        if len(vol_name) == 2 or len(vol_name) == 255:
            assert pos.cli.mount_volume(
                array_name=array_name, volumename=vol_name)[0] == True
            assert pos.cli.unmount_volume(
                array_name=array_name, volumename=vol_name)[0] == True

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("volnum", [255, 257])
def test_multiple_volume_create(volnum):
    '''The purpose of test is to create multiple volumes '''

    logger.info("================ Test : test_multiple_volume =================")
    try:
        if volnum > 256:
            assert pos.target_utils.create_volume_multiple(
                array_name=array_name, num_vol=256, size="10gb"
            ) == True

            assert pos.cli.create_volume(
                array_name=array_name, size="10gb", volumename="invalid-vol"
            )[0] == False

        else:

            assert pos.target_utils.create_volume_multiple(
                array_name=array_name, num_vol=volnum, size="10gb"
            ) == True

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_duplicate_name():
    '''The purpose is to create volume with duplicate names'''

    logger.info(
        "================ Test : test_volume_create_duplicate_name =================")

    try:

        assert pos.cli.create_volume(
            array_name=array_name, size="10gb", volumename="vol-duplicate"
        )[0] == True

        assert pos.cli.create_volume(
            array_name=array_name, size="10gb", volumename="vol-duplicate"
        )[0] == False

        # Delete the existing volume and retry creating with same name
        assert pos.cli.delete_volume(
            array_name=array_name, volumename="vol-duplicate"
        )[0] == True

        assert pos.cli.create_volume(
            array_name=array_name, size="10gb", volumename="vol-duplicate"
        )[0] == True

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_lt_aligned_blocksize():
    ''' The purpose of test is to create volume less than aligned block size '''

    logger.info(
        "================ Test : test_volume_create_size_lt_aligned =================")
    try:
        # 1MB = 1024 * 1024 Bytes
        # Less than 1MB => Unaligned blocksize
        assert pos.cli.create_volume(
            array_name=array_name, size="1024B", volumename="invalid-vol"
        )[0] == False

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_gt_max_array_capacity():
    ''' The purpose of test is to create volume exceeding max array capacity '''

    logger.info(
        "================ Test : test_volume_gt_array_capacity =================")
    try:
        num_vol = 255
        assert pos.cli.info_array(array_name=array_name)[0] == True
        array_size = int(pos.cli.array_info[array_name].get("size"))
        vol_size = f"{int((array_size // num_vol) // (1024 * 1024))}mb"
        assert pos.target_utils.create_volume_multiple(
            array_name=array_name, num_vol=255, size=vol_size
        ) == True

        # 255 Volumes used up the Max array Capacity
        # Creating 256th Volume with exceeded array capacity

        assert pos.cli.create_volume(
            array_name=array_name, size="10gb", volumename="invalid-vol"
        )[0] == False

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_array_create_with_invalid_uram():
    ''' The pupose of testcase is to create an array with invalid uram '''

    logger.info(
        "================ Test : test_array_create_with_invalid_uram =================")
    try:
        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        assert pos.cli.create_array(write_buffer="uram-invalid",
                                    data=data_disk_list,
                                    spare=None,
                                    raid_type="RAID5",
                                    array_name="invalid_" + array_name,
                                    )[0] == False

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_volume_create_without_array_mount():
    ''' The purpose of test is to create a volume on unmounted array'''

    logger.info(
        "================ Test : test_volume_create_without_array_mount =================")
    try:

        # unmount the array
        assert pos.cli.unmount_array(
            array_name=array_name,
        )[0] == True

        assert pos.cli.create_volume(
            array_name=array_name, size="10gb", volumename="invalid-vol"
        )[0] == False

        # mount the array
        assert pos.cli.mount_array(
            array_name=array_name,
        )[0] == True

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)
        assert 0
