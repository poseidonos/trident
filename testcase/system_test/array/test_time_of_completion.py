from common_libs import *
import logger
logger = logger.get_logger(__name__)
import random
from datetime import datetime

def create_array_and_volumes(pos, raid_types, data_disks, spare_disks, num_array=None):
    assert multi_array_data_setup(data_dict=pos.data_dict, num_array=num_array,
                                  raid_types=raid_types,
                                  num_data_disks=data_disks,
                                  num_spare_disk=spare_disks,
                                  auto_create=(True, True),
                                  array_mount=("WT", "WT")) == True

    assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

    assert pos.cli.array_list()[0] == True

    assert pos.target_utils.get_subsystems_list() == True

    assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=pos.cli.array_dict.keys(),
                                            subs_list=pos.target_utils.ss_temp_list) == True
    return True

def test_check_mount_and_unmount_pos_time(array_fixture):
    pos = array_fixture
    try:
        assert create_array_and_volumes(pos=pos,num_array=2,raid_types=('RAID5','RAID5'),data_disks=(3,3),spare_disks=(0,0)) == True
        arrays = list(pos.cli.array_dict.keys())
        for array in arrays:
            start_time = datetime.now()
            assert pos.cli.unmount_array(array_name=array)[0] == True
            end_time = datetime.now()
            time_taken = end_time - start_time
            function_minutes = divmod(time_taken.seconds, 60)
            logger.info(f"Time taken to unmount {array} : {function_minutes[0]} minutes {function_minutes[1]} seconds")
            start_time = datetime.now()
            assert pos.cli.mount_array(array_name=array)[0] == True
            end_time = datetime.now()
            time_taken = end_time - start_time
            mount_time = divmod(time_taken.seconds, 60)
            logger.info(f"Time taken to mount {array} : {mount_time[0]} minutes {mount_time[1]} seconds")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_check_pos_functionalities(array_fixture):
    pos = array_fixture
    try:
        assert create_array_and_volumes(pos=pos,num_array=1, raid_types=('RAID5',), data_disks=(3, ),
                                        spare_disks=(0, )) == True
        arrays = list(pos.cli.array_dict.keys())
        start_rebuild_time = datetime.now()
        assert array_disks_hot_remove(pos=pos,array_name=arrays[0],disk_remove_interval_list=[(0,)]) == True
        assert pos.target_utils.array_rebuild_wait(array_name=arrays[0],wait_time=2) == True
        end_rebuild_time = datetime.now()
        rebuild_duration = end_rebuild_time - start_rebuild_time
        rebuild_minutes = divmod(rebuild_duration.seconds, 60)
        logger.info(f"Time to rebuild {arrays[0]} : {rebuild_minutes[0]} minutes {rebuild_minutes[1]} seconds")
        assert array_add_spare_disk(pos=pos,array_list=arrays,verify=False) == True
        assert pos.target_utils.array_rebuild_wait(array_name=arrays[0])
        assert pos.cli.list_volume(array_name=arrays[0])[0] == True
        vols = pos.cli.vols
        for vol in vols:
            assert pos.cli.unmount_volume(volumename=vol,array_name=arrays[0])[0] == True
            assert pos.cli.delete_volume(volumename=vol, array_name=arrays[0])[0] == True
        pos.data_dict['volume']['pos_volumes'][0]['num_vol'] = 256
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        nvme_devs = nvme_connect(pos=pos)[1]
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=50 --verify=md5"
        out, async_io = pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd, run_async=True)
        assert out == True
        start_rebuild_time = datetime.now()
        assert array_disks_hot_remove(pos=pos, array_name=arrays[0], disk_remove_interval_list=[(0,)]) == True
        assert pos.target_utils.array_rebuild_wait(array_name=arrays[0], wait_time=2) == True
        end_rebuild_time = datetime.now()
        rebuild_duration = end_rebuild_time - start_rebuild_time
        rebuild_minutes = divmod(rebuild_duration.seconds, 60)
        logger.info(f"Time to rebuild {arrays[0]} : {rebuild_minutes[0]} minutes {rebuild_minutes[1]} seconds")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def time_taken(start_time,end_time,function):
    function_time = end_time - start_time
    function_time = divmod(function_time.seconds, 60)
    logger.info(f"Time taken to {function} : {function_time[0]} minutes {function_time[1]} seconds")

@pytest.mark.parametrize("pos_function",["unmount_vol","mount_vol","delete_vol"])
def test_time_taken_for_volume_deletion(array_fixture,pos_function):
    pos = array_fixture
    try:
        assert create_array_and_volumes(pos=pos, num_array=1, raid_types=('RAID5',), data_disks=(3,),
                                        spare_disks=(0,)) == True
        arrays = list(pos.cli.array_dict.keys())


        assert pos.cli.volume_list(array_name=arrays[0])[0] == True
        for vol_name in pos.cli.vol_dict.keys():
                if pos_function == "unmount_vol":
                    start_time = datetime.now()
                    assert pos.cli.volume_unmount(vol_name,
                                                  array_name=arrays[0])[0] == True
                if pos_function == "mount_vol":
                    assert pos.cli.volume_unmount(vol_name,
                                                  array_name=arrays[0])[0] == True
                    start_time = datetime.now()
                    assert pos.cli.volume_mount(vol_name,
                                                array_name=arrays[0])[0] == True
                if pos_function == "delete_vol":
                    assert pos.cli.volume_unmount(vol_name,
                                                  array_name=arrays[0])[0] == True
                    start_time = datetime.now()
                    assert pos.cli.volume_delete(vol_name,
                                                 array_name=arrays[0])[0] == True
        end_time = datetime.now()
        time_taken(start_time=start_time,end_time=end_time,function=pos_function)
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)