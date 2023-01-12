import pytest
import traceback

from pos import POS
import logger
import random
import time
import pprint

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["array"]["pos_array"][0]["data_device"] = 4
    data_dict["array"]["pos_array"][0]["spare_device"] = 0
    data_dict["array"]["pos_array"][0]["raid_type"] = "RAID10"
    data_dict["volume"]["pos_volumes"][0]["num_vol"] = 2
    data_dict["volume"]["pos_volumes"][1]["num_vol"] = 2
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.array_list()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.array_unmount(array_name=array)[0] == True
            assert pos.cli.array_delete(array_name=array)[0] == True
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True
            system_disks = pos.cli.system_disks
            if len(system_disks) < 4:
                pytest.skip(
                    f"Insufficient disk count {system_disks}. Required minimum {4 + 1}")
            data_disk_list = [system_disks.pop(0) for i in range(4)]
            spare_disk_list = []
            assert pos.cli.array_create(array_name=array,write_buffer='uram'+str(array_list.index(array)),data=data_disk_list,spare=spare_disk_list,raid_type="RAID10")[0] == True
            assert pos.cli.array_mount(array_name=array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name=array,vol_name='pos_vol',num_vol=2,size='1gb') == True
            assert pos.cli.volume_list(array_name=array)[0] == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.target_utils.mount_volume_multiple(array_name=array,volume_list=pos.cli.vols,nqn_list=[pos.target_utils.ss_temp_list[array_list.index(array)]]) == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

def run_block_io():
    for ss in pos.target_utils.ss_temp_list:
        assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
        )

    assert pos.client.nvme_list() == True

    # Run Block IO for an Hour
    fio_out = pos.client.fio_generic_runner(
        pos.client.nvme_list_out,
        fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=3",
    )
    return fio_out[0]


######################################SPS-3862#################################
raid_type = "RAID5"
nr_data_drives = 3
def test_array_recreation_to_diff_raid_type():
    assert run_block_io() == True
    assert pos.cli.array_list()[0] ==True
    array_list = list(pos.cli.array_dict.keys())
    for array in list(pos.cli.array_dict.keys()):
        assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = [system_disks.pop(0)]
        assert pos.cli.array_create(array_name=array,raid_type=raid_type,write_buffer='uram'+str(array_list.index(array)),data=data_disk_list,spare=spare_disk_list)[0] == True
        assert pos.cli.array_mount(array_name=array)[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_create(volumename=array + 'vol', size='1gb', array_name=array)[0] == True
        assert pos.cli.volume_mount(array_name=array, volumename=array + 'vol',nqn=pos.target_utils.ss_temp_list[array_list.index(array)])[0] == True
    assert run_block_io() == True

###########################################SPS-3863###########################################

def test_npor_raid10_arrays():
    assert run_block_io() == True
    assert pos.target_utils.npor() == True
    assert pos.cli.array_list()[0] ==True
    array_list = list(pos.cli.array_dict.keys())
    for array in list(pos.cli.array_dict.keys()):
        assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True
        assert pos.cli.devel_resetmbr()[0] == True
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = [system_disks.pop(0)]
        assert pos.cli.array_create(write_buffer="uram"+str(array_list.index(array)),raid_type=raid_type,data=data_disk_list,spare=spare_disk_list)[0] == True
        assert pos.cli.array_mount(array_name=array)[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_create(volumename=array+'vol',size='1gb',array_name=array)[0] == True
        assert pos.cli.volume_mount(array_name=array,volumename=array+'vol',nqn=pos.target_utils.ss_temp_list[array_list.index(array)])[0] == True
    assert run_block_io() == True

#############################################SPS-3889###################################################

raid_type = "RAID5"
nr_data_drives = 4
def test_replace_first_array_raid5():
    assert run_block_io() == True
    assert pos.cli.array_list()[0] == True
    first_array = list(pos.cli.array_dict.keys())[0]
    assert pos.cli.array_unmount(array_name=first_array)[0] == True
    assert pos.cli.array_delete(array_name=first_array)[0] == True
    assert pos.cli.device_scan()[0] == True
    assert pos.cli.device_list()[0] == True
    assert pos.cli.devel_resetmbr()[0] == True
    system_disks = pos.cli.system_disks
    if len(system_disks) < (nr_data_drives + 1):
        pytest.skip(
            f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
        )
    data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
    assert pos.cli.array_create(array_name=first_array, raid_type=raid_type, data=data_disk_list,spare=[],write_buffer="uram0")[0] == True
    assert pos.cli.array_mount(array_name=first_array)[0] == True
    assert pos.target_utils.create_volume_multiple(array_name=first_array,num_vol=2,vol_name='vol',size='1gb') == True
    assert pos.cli.volume_list(array_name=first_array)[0] == True
    assert pos.target_utils.get_subsystems_list() == True
    assert pos.target_utils.mount_volume_multiple(array_name=first_array,volume_list=pos.cli.vols,nqn_list=[pos.target_utils.ss_temp_list[0]])
