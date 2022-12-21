from common_libs import *
import logger
logger = logger.get_logger(__name__)
import random

TESTCASE_LIST={}
TESTCASE_LIST["SPS_4626"] = {"ARRAYS":{"RAID_TYPES":("RAID5","RAID6"),"NUM_DATA_DRIVES":(4,4),"NUM_SPARE":(2,2)},"SITUATION":("REBUILDING","REBUILDING")}
TESTCASE_LIST["SPS_4627"] = {"ARRAYS":{"RAID_TYPES":("RAID10","RAID5"),"NUM_DATA_DRIVES":(4,4),"NUM_SPARE":(2,2)},"SITUATION":("REBUILDING","REBUILDING")}
TESTCASE_LIST["SPS_4628"] = {"ARRAYS":{"RAID_TYPES":("RAID6","RAID5"),"NUM_DATA_DRIVES":(4,4),"NUM_SPARE":(2,0)},"SITUATION":("REBUILDING","DEGRADED")}
TESTCASE_LIST["SPS_4629"] = {"ARRAYS":{"RAID_TYPES":("RAID10","RAID5"),"NUM_DATA_DRIVES":(4,4),"NUM_SPARE":(2,0)},"SITUATION":("REBUILDING","DEGRADED")}
TESTCASES = [
    "SPS_4626","SPS_4627","SPS_4628","SPS_4629"
]
@pytest.mark.parametrize("testcase",TESTCASES)
def test_nft_quick_rebuild_while_io_running(array_fixture,testcase):
    pos = array_fixture
    assert multi_array_data_setup(data_dict=pos.data_dict, num_array=2, raid_types=TESTCASE_LIST[testcase]["ARRAYS"]["RAID_TYPES"],
                                        num_data_disks=TESTCASE_LIST[testcase]["ARRAYS"]["NUM_DATA_DRIVES"], num_spare_disk=TESTCASE_LIST[testcase]["ARRAYS"]["NUM_SPARE"], auto_create=(False, False),
                                        array_mount=("WT", "WT")) == True
    assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
    assert pos.cli.list_array()[0] == True
    assert pos.target_utils.get_subsystems_list() == True
    assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=pos.cli.array_dict.keys(),
                                                  subs_list=pos.target_utils.ss_temp_list) == True
    nvme_devs = nvme_connect(pos=pos)[1]
    fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=50 --verify=md5"
    out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                  fio_user_data=fio_cmd, run_async=True)
    assert out == True

    logger.info("*************** Sleep for 5 min ***************")
    time.sleep(100)
    #Replace data drive of the first array
    arrays = list(pos.cli.array_dict.keys())
    assert pos.cli.info_array(array_name=arrays[0])[0] == True
    data_dev = random.choice(list(pos.cli.array_info[arrays[0]]['data_list']))
    logger.info("*************** Triggering device replacement ***************")
    assert pos.cli.replace_drive_array(array_name=arrays[0], device_name=data_dev)[0] == True
    assert pos.target_utils.check_rebuild_status(array_name=arrays[0]) == True
    assert pos.cli.info_array(array_name=arrays[0])[0] == True
    assert pos.cli.array_info[arrays[0]]['situation'] ==  TESTCASE_LIST[testcase]["SITUATION"][0]
    #Hot remove the data drive of second array
    assert array_disks_hot_remove(pos=pos, array_name=arrays[1], disk_remove_interval_list=[(0,)]) == True
    assert pos.cli.info_array(array_name=arrays[1])[0] == True
    assert pos.cli.array_info[arrays[1]]['situation'] == TESTCASE_LIST[testcase]["SITUATION"][1]
    #Wait for rebuild to complete
    assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True
    assert pos.target_utils.array_rebuild_wait_multiple(array_list=arrays) == True
    for array in arrays:
        assert pos.target_utils.deleteAllVolumes(arrayname=array) == True
        assert pos.cli.info_array(array_name=array)[0] == True
    logger.info(
        " ============================= Test ENDs =============================")
