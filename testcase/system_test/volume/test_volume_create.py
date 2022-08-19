from tempfile import TemporaryFile
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

    global pos, data_dict, array_name
    pos = POS("pos_config.json")
    data_dict = pos.data_dict

    data_dict['array']['num_array'] = 1
    data_dict['volume']['phase'] = "false"
    data_dict['subsystem']['pos_subsystems'][0]['nr_subsystems'] = 1
    data_dict['subsystem']['pos_subsystems'][1]['nr_subsystems'] = 0
    array_name = data_dict["array"]["pos_array"][0]["array_name"]

    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")

    assert pos.cli.list_volume(array_name=array_name)[0] == True
    for vol in pos.cli.vols:
        assert pos.cli.delete_volume(
            volumename=vol, array_name=array_name)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
@pytest.mark.parametrize("vol_name, expected_res", [
    (generate_volume_name(3), True),
    (" ", False),
    (generate_volume_name(3)+"  "+generate_volume_name(3), True),
    (generate_volume_name(3), True),
    (generate_volume_name(3)+"  ", True),
    (generate_volume_name(254), True),
    (generate_volume_name(1), False),
    (generate_volume_name(255), True)
])
def test_volume_create(vol_name, expected_res):
    '''The purpose of testcase is to create volume with different names'''

    logger.info("================= Test: test_volume_create  =================")

    try:

        assert pos.cli.create_volume(
            volumename=vol_name, size="10gb", array_name=array_name)[0] == expected_res
        assert pos.cli.info_volume(array_name=array_name, vol_name=vol_name)[
            0] == expected_res

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
