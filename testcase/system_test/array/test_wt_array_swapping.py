import pytest
import random
import logger

logger = logger.get_logger(__name__)

def create_initial_arrays(pos, array_detail, arrays):
    assert pos.cli.devel_resetmbr()[0] == True
    for index, array_name in enumerate(arrays):
        assert pos.cli.device_scan()[0] == True 
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (array_detail[index][1]):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {array_detail[index][1] + 1}"
            )
        if array_detail[index][0] in ["NONE","RAID0"]:
            data_disk_list = [system_disks.pop(0) for i in range(array_detail[index][1])]
            spare_disk_list = []
        else:
            data_disk_list = [system_disks.pop(0) for i in range(array_detail[index][1])]
            spare_disk_list = [system_disks.pop(0)]

        buffer_device = f"uram{index}"
        raid_type = array_detail[index][0]
        assert pos.cli.array_create(array_name=array_name,
                                    write_buffer=buffer_device,
                                    data=data_disk_list,
                                    spare=spare_disk_list,
                                    raid_type=raid_type)[0] == True

        assert pos.cli.array_mount(array_name=array_name,
                                   write_back=False)[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        if len(pos.target_utils.ss_temp_list) >= len(arrays):
            assert pos.cli.volume_create(array_name=array_name,
                                         volumename=array_name+'vol',
                                         size='1gb')[0] == True
            subsys_list = pos.target_utils.ss_temp_list
            ss_list = [ss for ss in subsys_list if array_name in ss]
            nqn = ss_list[0]
            assert pos.cli.volume_mount(array_name=array_name,
                                        volumename=array_name+'vol',
                                        nqn=nqn)[0] == True
        else:
            logger.error("Not enough subsystems")


def run_block_io(pos):
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
def test_array_swapping(array_fixture, array_detail):
    try:
        pos = array_fixture
        array1_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        array2_name = pos.data_dict["array"]["pos_array"][1]["array_name"]
        arrays = [array1_name, array2_name]
        ss_list = pos.target_utils.ss_temp_list

        create_initial_arrays(pos, array_detail, arrays)
        assert run_block_io(pos) == True
        assert pos.client.nvme_disconnect(nqn=ss_list) == True
        assert pos.cli.array_list()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.array_unmount(array_name=array)[0] == True
            assert pos.cli.array_delete(array_name=array)[0] == True
        swapped_arrays = array_detail[::-1]
        create_initial_arrays(pos, swapped_arrays, arrays)
        assert run_block_io(pos) == True
        assert pos.cli.array_list()[0] == True
        arrays = list(pos.cli.array_dict.keys())
        assert pos.cli.array_info(array_name=arrays[0])[0] == True
        remove_drives = [random.choice(pos.cli.array_data[arrays[0]]["data_list"])]
        assert pos.target_utils.device_hot_remove(device_list=remove_drives) == True
        assert pos.target_utils.array_rebuild_wait(array_name=arrays[0]) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.parametrize("array_detail",[(1,1),(2,4)])
def test_raid10_creation_with_diff_num_drives(array_fixture, array_detail):
    try:
        pos = array_fixture
        array1_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        array2_name = pos.data_dict["array"]["pos_array"][1]["array_name"]
        arrays = [array1_name, array2_name]
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
                        array_name=arrays[array],
                        write_buffer="uram"+str(array),
                        data=data_disk_list,
                        spare=spare_disk_list,
                        raid_type=raid_type,
                    )[0]
                    != bool(num_of_drives%2)
            )
            assert pos.cli.array_mount(array_name=arrays[array])[0] != bool(num_of_drives % 2)

            assert pos.cli.array_list()[0] == True
            
            if len(list(pos.cli.array_dict.keys())) > 0:
                assert pos.cli.volume_create(array_name=arrays[array],
                                            volumename=arrays[array]+'vol',
                                            size='10gb')[0] == True
                assert pos.cli.volume_mount(array_name=arrays[array],
                                            volumename=arrays[array]+'vol',
                                            nqn=pos.target_utils.ss_temp_list[array])
        assert run_block_io(pos) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_creation_of_raid10_with_same_drives(array_fixture):
    try:
        pos = array_fixture
        array1_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        array2_name = pos.data_dict["array"]["pos_array"][1]["array_name"]
        num_of_drives = 4
        raid_type= "RAID10"
        assert pos.cli.devel_resetmbr()[0] == True
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < num_of_drives:
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {num_of_drives}")
        data_disk_list = [system_disks.pop(0) for i in range(num_of_drives)]

        assert pos.cli.array_create(array_name=array1_name,
                        write_buffer="uram0", data=data_disk_list,
                        spare=[], raid_type=raid_type)[0] == True
        
        assert pos.cli.array_mount(array_name=array1_name)[0] == True
        status = pos.cli.array_create(array_name=array2_name,
                        write_buffer="uram1", data=data_disk_list,
                        spare=[], raid_type=raid_type)
        assert status[0] == False
        event_name = status[1]['output']['Response']['result']['status']['eventName']
        logger.info(f"Expected failure for array create due to {event_name}")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_array_create_raid10_and_raid5(array_fixture):
    try:
        pos = array_fixture
        array1_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        array2_name = pos.data_dict["array"]["pos_array"][1]["array_name"]
        arrays = [array1_name, array2_name]
        array_details = [("RAID10",4),("RAID5",4)]
        create_initial_arrays(pos, array_details, arrays)
        assert run_block_io(pos) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_array_create_and_trigger_rebuild(array_fixture):
    try:
        pos = array_fixture
        array1_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        array2_name = pos.data_dict["array"]["pos_array"][1]["array_name"]
        arrays = [array1_name, array2_name]
        config_1 = [("RAID10",4),("RAID10",4)]
        config_2 = [("RAID10",4),("RAID5",3)]
        ss_list = pos.target_utils.ss_temp_list
        create_initial_arrays(pos,config_1, arrays)
        assert pos.cli.array_list()[0] == True
        assert run_block_io(pos) == True
        assert pos.client.nvme_disconnect(nqn=ss_list) == True
        assert pos.target_utils.spor() == True
        array_list = list(pos.cli.array_dict.keys())
        for array in array_list:
            assert pos.cli.array_unmount(array_name=array)[0] == True
            assert pos.cli.array_delete(array_name=array)[0] == True
        create_initial_arrays(pos, config_2, arrays)
        assert run_block_io(pos) == True
        assert pos.cli.array_info(array_name=array_list[1])[0] == True
        remove_drives = [random.choice(pos.cli.array_data[array_list[1]]["data_list"])]
        assert pos.target_utils.device_hot_remove(device_list=remove_drives)
        assert pos.cli.array_info(array_name=array_list[1])
        if pos.cli.array_data[array_list[1]]["state"] == 'BUSY' and pos.cli.array_data[array_list[1]]["situation"] == 'REBUILDING':
            pos.target_utils.array_rebuild_wait(array_name=array_list[1])
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
