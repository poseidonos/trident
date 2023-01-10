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
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
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
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.array_unmount(array_name=array)[0] == True
                assert pos.cli.array_delete(array_name=array)[0] == True
            else:
                assert pos.cli.array_delete(array_name=array)[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

arrays = ["POSARRAY1", "POSARRAY2"]
nqn_name = "nqn.2022-10-array1.pos:subsystem"
def create_initial_arrays(array_detail):
    array_name = ["POSARRAY1","POSARRAY2"]
    assert pos.cli.devel_resetmbr()[0] == True
    for array in range(len(array_name)):
        assert pos.cli.device_scan()[0] == True 
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (array_detail[array][1]):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {array_detail[array][1] + 1}"
            )
        if array_detail[array][0] in ["NONE","RAID0"]:
            data_disk_list = [system_disks.pop(0) for i in range(array_detail[array][1])]
            spare_disk_list = []
        else:
            data_disk_list = [system_disks.pop(0) for i in range(array_detail[array][1])]
            spare_disk_list = [system_disks.pop(0)]
        if array == 1:
            buffer_device = "uram0"
        else:
            buffer_device = "uram1"
        assert (
                pos.cli.array_create(
                    write_buffer=buffer_device,
                    data=data_disk_list,
                    spare=spare_disk_list,
                    raid_type=array_detail[array][0],
                    array_name=array_name[array],
                )[0]
                == True
        )

        assert pos.cli.array_mount(array_name=array_name[array], write_back=False)[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        if len(pos.target_utils.ss_temp_list) >= len(array_name):
            assert pos.cli.volume_create(array_name=array_name[array],volumename=array_name[array]+'vol',size='1gb')[0] == True
            assert pos.cli.volume_mount(array_name=array_name[array],volumename=array_name[array]+'vol',nqn=pos.target_utils.ss_temp_list[array])[0] == True
        else:
            logger.error("Not enough subsystems")


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
        fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
    )
    return fio_out[0]

@pytest.mark.parametrize("array_detail",[[("RAID10",4),("NONE",1)],[("RAID10",4),("RAID0",2)],[("RAID10",4),("RAID5",3)]])
def test_array_swapping(array_detail):
    create_initial_arrays(array_detail)
    assert run_block_io() == True
    assert pos.cli.array_list()[0] == True
    for array in list(pos.cli.array_dict.keys()):
        assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True
    swapped_arrays = array_detail[::-1]
    create_initial_arrays(swapped_arrays)
    assert run_block_io() == True
    assert pos.cli.array_list()[0] == True
    arrays = list(pos.cli.array_dict.keys())
    assert pos.cli.array_info(array_name=arrays[0])[0] == True
    remove_drives = [random.choice(pos.cli.array_data[arrays[0]]["data_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives) == True
    assert pos.target_utils.array_rebuild_wait(array_name=arrays[0]) == True 


@pytest.mark.parametrize("array_detail",[(1,1),(2,4)])
def test_raid10_creation_with_diff_num_drives(array_detail):
    num_of_array = array_detail[0]
    num_of_drives = array_detail[1]
    raid_type = "RAID10"
    bool_op = [True,False]
    assert pos.cli.devel_resetmbr()[0] == True
    for array in range(num_of_array):
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (num_of_drives):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {num_of_drives + 1}")
        data_disk_list = [system_disks.pop(0) for i in range(num_of_drives)]
        spare_disk_list = []
        assert pos.target_utils.get_subsystems_list() == True
        assert (
                pos.cli.array_create(
                    write_buffer="uram"+str(array),
                    data=data_disk_list,
                    spare=spare_disk_list,
                    raid_type=raid_type,
                    array_name=arrays[array],
                )[0]
                != bool(num_of_drives%2)
        )
        assert pos.cli.array_mount(array_name=arrays[array])[0] != bool(num_of_drives % 2)

        assert pos.cli.array_list()[0] == True
        if len(list(pos.cli.array_dict.keys())) > 0:
            assert pos.cli.volume_create(array_name=arrays[array],volumename=arrays[array]+'vol',size='10gb')[0] == True
            assert pos.cli.volume_mount(array_name=arrays[array],volumename=arrays[array]+'vol',nqn=pos.target_utils.ss_temp_list[array])
            assert run_block_io() == True

def test_creation_of_raid10_with_same_drives():
    num_of_drives = 4
    raid_type= "RAID10"
    assert pos.cli.devel_resetmbr()[0] == True
    assert pos.cli.device_scan()[0] == True
    assert pos.cli.device_list()[0] == True
    system_disks = pos.cli.system_disks
    if len(system_disks) < (num_of_drives):
        pytest.skip(
            f"Insufficient disk count {system_disks}. Required minimum {num_of_drives + 1}")
    data_disk_list = [system_disks.pop(0) for i in range(num_of_drives)]
    spare_disk_list = []
    assert pos.cli.array_create(write_buffer="uram0",data=data_disk_list,spare=spare_disk_list,raid_type=raid_type,array_name=arrays[0])[0] == True
    assert pos.cli.array_mount(array_name=arrays[0])[0] == True
    assert pos.cli.array_create(write_buffer="uram1",data=data_disk_list,spare=spare_disk_list,raid_type=raid_type,array_name=arrays[1])[0] == False


def test_array_create_raid10_and_raid5():
    array_details = [("RAID10",4),("RAID5",4)]
    create_initial_arrays(array_details)
    assert run_block_io() == True

def test_array_create_and_trigger_rebuild():
    config_1 = [("RAID10",4),("RAID10",4)]
    config_2 = [("RAID10",4),("RAID5",3)]
    create_initial_arrays(config_1)
    assert pos.cli.array_list()[0] == True
    assert run_block_io() == True
    assert pos.target_utils.Spor() == True
    array_list = list(pos.cli.array_dict.keys())
    for array in array_list:
        assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True
    create_initial_arrays(config_2)
    assert run_block_io() == True
    assert pos.cli.array_info(array_name=array_list[1])[0] == True
    remove_drives = [random.choice(pos.cli.array_data[array_list[1]]["data_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives)
    assert pos.cli.array_info(array_name=array_list[1])
    if pos.cli.array_data[array_list[1]]["state"] == 'BUSY' and pos.cli.array_data[array_list[1]]["situation"] == 'REBUILDING':
        pos.target_utils.array_rebuild_wait(array_name=array_list[1])
