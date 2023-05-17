import pytest
import logger


logger = logger.get_logger(__name__)


def array_setup(pos):
    data_dict = pos.data_dict
    data_dict["array"]["pos_array"][0]["data_device"] = 4
    data_dict["array"]["pos_array"][0]["spare_device"] = 0
    data_dict["array"]["pos_array"][0]["raid_type"] = "RAID10"
    assert pos.target_utils.bringup_array(data_dict=data_dict) == True
    assert pos.target_utils.bringup_volume(data_dict=data_dict) == True


def array_reset(pos):
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.array_list()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for index, array in enumerate(array_list):
            assert pos.cli.array_unmount(array_name=array)[0] == True
            assert pos.cli.array_delete(array_name=array)[0] == True
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True
            system_disks = pos.cli.system_disks
            if len(system_disks) < 4:
                pytest.skip(
                    f"Insufficient disk count {system_disks}. Required minimum {4 + 1}")
            data_disk_list = [system_disks.pop(0) for i in range(4)]
            assert pos.cli.array_create(array_name=array,
                                        write_buffer=f'uram{index}',
                                        data=data_disk_list, spare=[],
                                        raid_type="RAID10")[0] == True
            assert pos.cli.array_mount(array_name=array)[0] == True

            assert pos.target_utils.create_volume_multiple(array_name=array,
                            vol_name='pos_vol', num_vol=2,size='1gb') == True
            assert pos.cli.volume_list(array_name=array)[0] == True

            assert pos.target_utils.get_subsystems_list() == True
            ss_temp_list = pos.target_utils.ss_temp_list
            ss_list = [ss for ss in ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name=array,
                                volume_list=pos.cli.vols, nqn=ss_list[0]) == True
    logger.info("==========================================")



def run_block_io(pos):
    ip_addr = pos.target_utils.helper.ip_addr[0]
    for ss in pos.target_utils.ss_temp_list:
        assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

    assert pos.client.nvme_list() == True

    # Run Block IO for an Hour
    fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=120"
    fio_out = pos.client.fio_generic_runner(pos.client.nvme_list_out,
                                            fio_user_data=fio_cmd)

    assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    return fio_out[0]


######################################SPS-3862#################################
raid_type = "RAID5"
nr_data_drives = 3
def test_array_recreation_to_diff_raid_type(array_fixture):
    try:
        pos = array_fixture
        array_setup(pos)
        assert run_block_io(pos) == True
        assert pos.cli.array_list()[0] ==True
        for index, array in enumerate(pos.cli.array_dict.keys()):
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
            assert pos.cli.array_create(array_name=array,
                        write_buffer=f'uram{index}', data=data_disk_list,
                        spare=spare_disk_list, raid_type=raid_type)[0] == True
            
            assert pos.cli.array_mount(array_name=array)[0] == True
            assert pos.target_utils.get_subsystems_list() == True
            ss_temp_list = pos.target_utils.ss_temp_list
            ss_list = [ss for ss in ss_temp_list if array in ss]

            vol_name=array + 'vol'
            assert pos.cli.volume_create(volumename=vol_name, size='1gb',
                                         array_name=array)[0] == True
            assert pos.cli.volume_mount(array_name=array, 
                                volumename=vol_name, nqn=ss_list[0])[0] == True
        assert run_block_io(pos) == True
        array_reset(pos)
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

###########################################SPS-3863###########################################

def test_npor_raid10_arrays(array_fixture):
    try:
        pos = array_fixture
        array_setup(pos)
        assert run_block_io(pos) == True
        assert pos.target_utils.npor() == True
        assert pos.cli.array_list()[0] ==True
        array_list = list(pos.cli.array_dict.keys())
        for array in array_list:
            assert pos.cli.array_unmount(array_name=array)[0] == True
            assert pos.cli.array_delete(array_name=array)[0] == True

        for index, array in enumerate(array_list):
            assert pos.cli.device_scan()[0] == True
            assert pos.cli.device_list()[0] == True
            system_disks = pos.cli.system_disks
            if len(system_disks) < (nr_data_drives + 1):
                pytest.skip(
                    f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
                )
            data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
            spare_disk_list = [system_disks.pop(0)]
            assert pos.cli.array_create(array_name=array,
                        write_buffer=f'uram{index}', data=data_disk_list,
                        spare=spare_disk_list, raid_type=raid_type)[0] == True
            assert pos.cli.array_mount(array_name=array)[0] == True
            assert pos.target_utils.get_subsystems_list() == True
            vol_name = array+'vol'
            assert pos.cli.volume_create(volumename=vol_name, size='1gb',
                                         array_name=array)[0] == True
            ss_temp_list = pos.target_utils.ss_temp_list
            ss_list = [ss for ss in ss_temp_list if array in ss]
            assert pos.cli.volume_mount(array_name=array, volumename=vol_name,
                                        nqn=ss_list[0])[0] == True
        assert run_block_io(pos) == True
        array_reset(pos)
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

#############################################SPS-3889###################################################

raid_type = "RAID5"
nr_data_drives = 4
def test_replace_first_array_raid5(array_fixture):
    try:
        pos = array_fixture
        array_setup(pos)
        assert run_block_io(pos) == True
        assert pos.cli.array_list()[0] == True
        first_array = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.array_unmount(array_name=first_array)[0] == True
        assert pos.cli.array_delete(array_name=first_array)[0] == True
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        #assert pos.cli.devel_resetmbr()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        assert pos.cli.array_create(array_name=first_array,
                                    raid_type=raid_type,
                                    data=data_disk_list, spare=[],
                                    write_buffer="uram0")[0] == True
        assert pos.cli.array_mount(array_name=first_array)[0] == True
        assert pos.target_utils.create_volume_multiple(first_array,
                        num_vol=2,vol_name='vol',size='1gb') == True

        assert pos.cli.volume_list(array_name=first_array)[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        ss_temp_list = pos.target_utils.ss_temp_list
        ss_list = [ss for ss in ss_temp_list if first_array in ss]
        assert pos.target_utils.mount_volume_multiple(first_array,
                                                      volume_list=pos.cli.vols,
                                                      nqn=ss_list[0]) == True
        array_reset(pos)
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
