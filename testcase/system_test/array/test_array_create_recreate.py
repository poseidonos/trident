import pytest
import time
import random
import common_libs as io
import logger
logger = logger.get_logger(__name__)
from pos import POS
global pos
pos = POS()

def creation(pos,pos_dict,volume_creation=True,num_vols=2):
    assert pos.target_utils.bringupArray(pos_dict) == True
    if volume_creation == True:
        pos_dict['volume']['phase'] = 'true'
        for i in range(2):
            pos_dict["volume"]["pos_volumes"][i]["num_vol"] = num_vols
        assert pos.target_utils.bringupVolume(pos_dict) == True
    return True


def recreation(pos,initial_array_raid):
    array_spare = 0
    if initial_array_raid == "RAID0":
        array_drives = 2
        recreate_array = "RAID5"
        recreate_array_drive = 3
    else:
        array_drives = 3
        recreate_array = "RAID0"
        recreate_array_drive = 2

    for i in range(2):
        pos.data_dict["array"]["pos_array"][i]["raid_type"] = initial_array_raid
        pos.data_dict["array"]["pos_array"][i]["data_device"] = array_drives
        pos.data_dict["array"]["pos_array"][i]["spare_device"] = array_spare
    assert creation(pos=pos,pos_dict=pos.data_dict) == True
    assert io.run_io(pos=pos) == True
    assert pos.cli.list_array()[0] == True
    array_list =list(pos.cli.array_dict.keys())
    for array in array_list:
        assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.delete_array(array_name=array)[0] == True
        pos.data_dict["array"]["pos_array"][array_list.index(array)]["raid_type"] = recreate_array
        pos.data_dict["array"]["pos_array"][array_list.index(array)]["data_device"] = recreate_array_drive
        pos.data_dict["array"]["pos_array"][array_list.index(array)]["spare_device"] = array_spare
    assert creation(pos=pos, pos_dict=pos.data_dict) == True
    assert io.run_io(pos=pos) == True
    return True

@pytest.mark.regression
@pytest.mark.parametrize("raid_type",["RAID5","RAID0"])
def test_recreation_of_arrays(array_fixture,raid_type):
    assert recreation(pos=pos,initial_array_raid=raid_type) == True

@pytest.mark.regression
def test_multiple_recreation(array_fixture):
    pos = array_fixture
    for i in range(5):
        assert recreation(pos,"RAID5") == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.unmount_array(array_name=array)[0] == True
            assert pos.cli.delete_array(array_name=array)[0] == True

@pytest.mark.regression
def test_apply_log_filter(array_fixture):
    assert pos.cli.apply_log_filter()[0] == False

@pytest.mark.regression
def test_multiple_r0_array(array_fixture):
    pos.data_dict['array']['phase'] = 'true'
    for i in range(2):
        pos.data_dict['array']['pos_array'][i]["raid_type"] = "RAID0"
        pos.data_dict['array']['pos_array'][i]["data_device"] = 2
        pos.data_dict['array']['pos_array'][i]["spare_device"] = 0
    assert creation(pos=pos,pos_dict=pos.data_dict) == True
    assert io.run_io(pos=pos) == True

@pytest.mark.negative
def test_mount_invalid_volume_name(array_fixture):
    volume_name = 'pos_vol'
    invalid_volume_name = "inv@AL!-D"
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    assert creation(pos=pos,pos_dict=pos.data_dict,volume_creation=False) == True
    assert pos.cli.list_array()[0] == True
    array = list(pos.cli.array_dict.keys())[0]
    assert pos.cli.create_volume(volumename=volume_name,size='1gb',array_name=array)[0] == True
    assert pos.cli.mount_volume(volumename=invalid_volume_name,array_name=array )[0] == False

@pytest.mark.negative
def test_create_volume_with_invalid_name(array_fixture):
    invalid_volume_name = "inv@AL!-D"
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    assert creation(pos=pos,pos_dict=pos.data_dict,volume_creation=False) == True
    assert pos.cli.list_array()[0] == True
    array = list(pos.cli.array_dict.keys())[0]
    assert pos.cli.create_volume(volumename=invalid_volume_name,size='1gb',array_name=array)[0] == False

def test_detaching_drives_r0(array_fixture):
    pos.data_dict['array']['phase'] = 'true'
    for i in range(2):
        pos.data_dict['array']['pos_array'][i]['raid_type'] = "RAID0"
        pos.data_dict['array']['pos_array'][i]['data_device'] = 2
        pos.data_dict['array']['pos_array'][i]['spare_device'] = 0
    assert creation(pos=pos,pos_dict=pos.data_dict,volume_creation=True) == True
    assert io.run_io(pos=pos) == True
    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    assert pos.cli.info_array(array_name=list(pos.cli.array_dict.keys())[0])[0] == True
    remove_drives = [random.choice(pos.cli.array_info[array_list[0]]["data_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives) == True

def test_gc_on_r0(array_fixture):
    volume_name = 'pos_vol'
    invalid_volume_name = "inv@AL!-D"
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    assert creation(pos=pos, pos_dict=pos.data_dict, volume_creation=False) == True
    assert pos.cli.list_array()[0] == True
    array = list(pos.cli.array_dict.keys())[0]
    assert pos.cli.create_volume(volumename=volume_name, size='1gb', array_name=array)[0] == True
    assert pos.cli.mount_volume(volumename=invalid_volume_name, array_name=array)[0] == False
    pos.cli.wbt_do_gc()
    pos.cli.wbt_get_gc_status()[0]
    assert pos.cli.list_array()[0] == True

def test_array_in_degraded_state(array_fixture):
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    pos.data_dict['array']['pos_array'][0]['spare_device'] = 0
    assert creation(pos=pos, pos_dict=pos.data_dict) == True
    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    assert pos.cli.info_array(array_name=list(pos.cli.array_dict.keys())[0])[0] == True
    remove_drives = [random.choice(pos.cli.array_info[array_list[0]]["data_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives) == True
    assert pos.cli.info_array(array_name=array_list[0])[0] == True
    if pos.cli.array_info[array_list[0]]['situation'].upper() == "DEGRADED":
        assert io.run_io(pos=pos) == True
        pass


def test_remove_device_unmount_state(array_fixture):
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    assert creation(pos=pos, pos_dict=pos.data_dict) == True
    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    assert pos.cli.unmount_array(array_name=array_list[0])[0] == True
    assert pos.cli.info_array(array_name=array_list[0])[0] == True
    remove_drives = [random.choice(pos.cli.array_info[array_list[0]]["spare_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives) == True
    assert pos.cli.info_array(array_name=array_list[0])[0] == True
    assert pos.cli.mount_array(array_name=array_list[0])[0] == True
    assert pos.cli.info_array(array_name=array_list[0])[0] == True
    remove_drives = [random.choice(pos.cli.array_info[array_list[0]]["data_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives) == True
    assert pos.cli.info_array(array_name=array_list[0])[0] == True

@pytest.mark.parametrize("level",["debug","warning","error","off"])
def test_set_log_level(array_fixture,level):
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    assert pos.cli.set_log_level_logger(level=level)[0] == True
    assert creation(pos=pos, pos_dict=pos.data_dict, volume_creation=False) == True

@pytest.mark.regression
def test_unmount_array_in_degraded_state(array_fixture):
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    pos.data_dict['array']['pos_array'][0]['spare_device'] = 0
    assert creation(pos=pos, pos_dict=pos.data_dict) == True
    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    assert pos.cli.info_array(array_name=list(pos.cli.array_dict.keys())[0])[0] == True
    remove_drives = [random.choice(pos.cli.array_info[array_list[0]]["data_list"])]
    assert pos.target_utils.device_hot_remove(device_list=remove_drives) == True
    assert pos.cli.info_array(array_name=array_list[0])[0] == True
    if pos.cli.array_info[array_list[0]]['situation'].upper() == "DEGRADED":
        assert pos.cli.unmount_array(array_name=array_list[0])[0] == True

@pytest.mark.regression
def test_write_through_wt_r5(array_fixture):
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    pos.data_dict['array']['pos_array'][0]['write_back'] = 'false'
    assert creation(pos,pos_dict=pos.data_dict,num_vols=256) == True
    connect_status , nvme_devs = io.nvme_connect(pos=pos)
    fio_cmd = f"fio --name=sequential_write --ioengine=libaio --rw=write \
                                --iodepth=64 --direct=1 --bs=128k --size=1g"

    half = int(len(nvme_devs) / 2)
    file_io_devs = nvme_devs[0: half - 1]
    block_io_devs = nvme_devs[half: len(nvme_devs) - 1]
    assert pos.client.create_File_system(file_io_devs, fs_format="xfs")
    out, mount_point = pos.client.mount_FS(file_io_devs)
    assert out == True
    io_mode = False  # Set False this to File IO
    out, async_file_io = pos.client.fio_generic_runner(
        mount_point, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
    )
    assert out == True

    io_mode = True  # Set False this to Block IO
    out, async_block_io = pos.client.fio_generic_runner(
        block_io_devs, fio_user_data=fio_cmd, IO_mode=io_mode, run_async=True
    )
    assert out == True

    # Wait for async FIO completions
    while True:
        time.sleep(30)  # Wait for 30 seconds
        file_io = async_file_io.is_complete()
        block_io = async_block_io.is_complete()

        msg = []
        if not file_io:
            msg.append("File IO")
        if not block_io:
            msg.append("Block IO")

        if msg:
            logger.info(
                "'{}' is still running. Wait 30 seconds...".format(",".join(msg))
            )
            continue
        break

@pytest.mark.regression
def test_write_through_to_write_back(array_fixture):
    assert pos.target_utils.bringupSystem(pos.data_dict) == True
    pos.data_dict['array']['phase'] = 'true'
    pos.data_dict['array']['num_array'] = 1
    pos.data_dict['array']['pos_array'][0]['write_back'] = 'false'
    assert creation(pos, pos_dict=pos.data_dict,volume_creation=False) == True
    assert pos.cli.list_array()[0] == True
    arr_list = list(pos.cli.array_dict.keys())
    for i in range(1):
        assert pos.cli.unmount_array(array_name=arr_list[0])[0] == True
        assert pos.cli.mount_array(array_name=arr_list[0],write_back=True) == True
        assert pos.cli.unmount_array(array_name=arr_list[0])[0] == True
        assert pos.cli.mount_array(array_name=arr_list[0],write_back=False)[0] == True

