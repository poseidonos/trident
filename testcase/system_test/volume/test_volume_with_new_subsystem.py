from common_libs import *
import logger
logger = logger.get_logger(__name__)
import random
import string

def generate_random_name(len_name):
    '''Generate random name of length "len_name"'''

    return "".join(random.choices(string.digits, k=len_name))

def test_mount_vol_with_new_subsystem(array_fixture):
    pos = array_fixture
    try:
        pos.data_dict['array']['num_array'] = 1
        assert pos.target_utils.bringup_array(data_dict = pos.data_dict) == True
        array_list = list(pos.cli.array_dict.keys())
        nqn_name = 'nqn.2022-10.pos-array1:subsystem'+generate_random_name(10)
        assert volume_create_and_mount_multiple(pos=pos,num_volumes=256,vol_size='1GB',subs_list=[nqn_name],
                                                array_list=array_list,mount_vols=True) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)