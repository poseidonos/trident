from common_libs import *
import logger
logger = logger.get_logger(__name__)
import random
from node import SSHclient
from pos import POS
def setup_array_and_volumes(pos, raid_types, data_disks, spare_disks, num_array=None,num_volumes=1,io=True):
    assert multi_array_data_setup(data_dict=pos.data_dict, num_array=num_array,
                                  raid_types=raid_types,
                                  num_data_disks=data_disks,
                                  num_spare_disk=spare_disks,
                                  auto_create=(True, True),
                                  array_mount=("WT", "WT")) == True

    assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
    assert pos.cli.array_list()[0] == True
    assert pos.target_utils.get_subsystems_list() == True
    assert volume_create_and_mount_multiple(pos=pos, num_volumes=num_volumes, array_list=pos.cli.array_dict.keys(),
                                            subs_list=pos.target_utils.ss_temp_list) == True
    if io == True:
        assert vol_connect_and_run_random_io(pos=pos,subs_list=pos.target_utils.ss_temp_list) == True
    return True

def test_array_swapping(array_fixture):
    assert setup_array_and_volumes(pos=array_fixture,num_array=2,raid_types=('RAID5','RAID10'),data_disks=(4,4),spare_disks=(0,0)) == True
    # arrays = list(pos.cli.array_dict.keys())
    assert array_unmount_and_delete(pos=array_fixture) == True
    assert setup_array_and_volumes(pos=array_fixture, num_array=2, raid_types=('RAID10', 'RAID5'), data_disks=(4, 4),
                                   spare_disks=(0, 0),io = False) == True

minimum_crefi = ('1','1','1')
maximum_crefi = ('100','100','100')
@pytest.mark.parametrize("dir",[minimum_crefi,maximum_crefi])
def test_crefi_on_volumes(array_fixture,dir):
    assert setup_array_and_volumes(pos=array_fixture, num_array=1, raid_types=('RAID5',), data_disks=(4,),
                                   spare_disks=(0, ),io=False) == True
    assert run_crefi_on_all_volumes(pos=array_fixture,breadth=dir[0],depth=dir[1],files=dir[2]) == True


@pytest.mark.parametrize("num_volumes",[1,256])
@pytest.mark.parametrize("num_array",[1,2])
def test_reboot_feature(array_fixture,num_array,num_volumes):
    pos = array_fixture
    assert setup_array_and_volumes(pos=array_fixture, num_array=1, raid_types=('RAID5','RAID5'), data_disks=(4,4),
                                   spare_disks=(0,0),num_volumes=num_volumes, io=True) == True
    assert pos.target_utils.reboot_with_backup() == True
