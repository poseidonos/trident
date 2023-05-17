from common_libs import *
import logger
logger = logger.get_logger(__name__)
import random
import string
def generate_random_name(len_name):
    '''Generate random name of length "len_name"'''

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=len_name))

def test_mount_vol_with_new_subsystem(array_fixture):
    pos = array_fixture
    try:
        pos.data_dict['array']['num_array'] = 1
        assert pos.target_utils.bringupArray(data_dict = pos.data_dict) == True
        array_list = list(pos.cli.array_dict.keys())
        pos.data_dict['volume']['pos_volumes'][0]['num_vol'] = 255
        pos.data_dict['volume']['pos_volumes'][0]['mount'] = "false"
        assert pos.target_utils.bringupVolume(data_dict = pos.data_dict) == True
        nqn_name = pos.target_utils.generate_nqn_name()
        assert pos.cli.list_volume(array_name=pos.array_list[0])[0] == True
        assert pos.target_utils.mount_volume_multiple(array_name=pos.array_list[0],volume_list=pos.cli.vols,nqn=nqn_name) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)