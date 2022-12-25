from common_libs import *
import logger
logger = logger.get_logger(__name__)
import random


def create_array_and_volumes(pos,testcase,num_array=None):
    assert multi_array_data_setup(data_dict=pos.data_dict, num_array=num_array,
                                  raid_types=TESTCASE_LIST[testcase]["ARRAYS"]["RAID_TYPES"],
                                  num_data_disks=TESTCASE_LIST[testcase]["ARRAYS"]["NUM_DATA_DRIVES"],
                                  num_spare_disk=TESTCASE_LIST[testcase]["ARRAYS"]["NUM_SPARE"],
                                  auto_create=TESTCASE_LIST[testcase]["ARRAYS"]["AUTO_CREATE"],
                                  array_mount=TESTCASE_LIST[testcase]["ARRAYS"]["ARRAY_MOUNT"]) == True

    assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True

    assert pos.cli.list_array()[0] == True

    assert pos.target_utils.get_subsystems_list() == True

    assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=pos.cli.array_dict.keys(),
                                            subs_list=pos.target_utils.ss_temp_list) == True
    return True

def trigger_quick_rebuild(pos,array):
    # Replace data drive of the first array

    assert pos.cli.info_array(array_name=array)[0] == True

    data_dev = random.choice(list(pos.cli.array_info[array]['data_list']))

    logger.info("*************** Triggering device replacement ***************")

    assert pos.cli.replace_drive_array(array_name=array, device_name=data_dev)[0] == True

    return True

TESTCASE_LIST={}
TESTCASE_LIST["SPS_4626"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID5","RAID6"),
                                       "NUM_DATA_DRIVES":(4,4),
                                       "NUM_SPARE":(2,2),
                                       "AUTO_CREATE":(True, True),
                                       "ARRAY_MOUNT":("WT", "WT")},
                             "SITUATION":
                                 ("REBUILDING","REBUILDING")}
TESTCASE_LIST["SPS_4627"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID10","RAID5"),
                                       "NUM_DATA_DRIVES":(4,4),
                                       "NUM_SPARE":(2,2),
                                       "AUTO_CREATE":(True, True),
                                       "ARRAY_MOUNT":("WT", "WT")},
                             "SITUATION":
                                 ("REBUILDING","REBUILDING")}
TESTCASE_LIST["SPS_4628"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID6","RAID5"),
                                       "NUM_DATA_DRIVES":(4,4),
                                       "NUM_SPARE":(2,0),
                                       "AUTO_CREATE":(True, True),
                                       "ARRAY_MOUNT":("WT", "WT")},
                             "SITUATION":
                                 ("REBUILDING","DEGRADED")}
TESTCASE_LIST["SPS_4629"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID10","RAID5"),
                                       "NUM_DATA_DRIVES":(4,4),
                                       "NUM_SPARE":(2,0),
                                       "AUTO_CREATE":(True, True),
                                       "ARRAY_MOUNT":("WT", "WT")},
                             "SITUATION":
                                 ("REBUILDING","DEGRADED")}
TESTCASES = [
    "SPS_4626","SPS_4627","SPS_4628","SPS_4629"
]
@pytest.mark.parametrize("testcase",TESTCASES)
def test_nft_quick_rebuild_while_io_running(array_fixture,testcase):
    try:
        pos = array_fixture
        assert create_array_and_volumes(pos=pos,testcase=testcase,num_array=2) == True

        nvme_devs = nvme_connect(pos=pos)[1]

        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=50 --verify=md5"

        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                      fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("*************** Sleep for 5 min ***************")
        time.sleep(300)

        arrays = list(pos.cli.array_dict.keys())

        assert trigger_quick_rebuild(pos=pos,array=arrays[0]) == True

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
            assert pos.cli.info_array(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")

        pos.exit_handler(expected=False)



TESTCASE_LIST["SPS_4638"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID6",),
                                  "NUM_DATA_DRIVES":(4,),
                                  "NUM_SPARE":(2,),
                                  "AUTO_CREATE":(True,),
                                  "ARRAY_MOUNT":("WT",)},
                             "QUICK_REBUILD":2,
                             "POR":"SPOR"}
TESTCASE_LIST["SPS_4641"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID10",),
                                  "NUM_DATA_DRIVES":(4,),
                                  "NUM_SPARE":(2,),
                                  "AUTO_CREATE":(True,),
                                  "ARRAY_MOUNT":("WT",)},
                             "QUICK_REBUILD":2,
                             "POR":"SPOR"}
TESTCASE_LIST["SPS_4642"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID6",),
                                  "NUM_DATA_DRIVES":(4,),
                                  "NUM_SPARE":(2,),
                                  "AUTO_CREATE":(True,),
                                  "ARRAY_MOUNT":("WT",)},
                             "QUICK_REBUILD":2,
                             "POR":"NPOR"}
TESTCASE_LIST["SPS_4643"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID10",),
                                  "NUM_DATA_DRIVES":(4,),
                                  "NUM_SPARE":(2,),
                                  "AUTO_CREATE":(True,),
                                  "ARRAY_MOUNT":("WT",)},
                             "QUICK_REBUILD":2,
                             "POR":["NPOR"]}
TESTCASE_LIST["SPS_4647"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID5",),
                                  "NUM_DATA_DRIVES":(4,),
                                  "NUM_SPARE":(3,),
                                  "AUTO_CREATE":(True,),
                                  "ARRAY_MOUNT":("WT",)},
                             "QUICK_REBUILD":3,
                             "POR":["NPOR","SPOR"]}
TESTCASE_LIST["SPS_4649"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID6",),
                                  "NUM_DATA_DRIVES":(4,),
                                  "NUM_SPARE":(3,),
                                  "AUTO_CREATE":(True,),
                                  "ARRAY_MOUNT":("WT",)},
                             "QUICK_REBUILD":3,
                             "POR":["NPOR","SPOR"]}
TESTCASE_LIST["SPS_4650"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID6",),
                                  "NUM_DATA_DRIVES":(4,),
                                  "NUM_SPARE":(2,),
                                  "AUTO_CREATE":(True,),
                                  "ARRAY_MOUNT":("WT",)},
                             "QUICK_REBUILD":2}
TESTCASE_LIST["SPS_4651"] = {"ARRAYS":
                                 {"RAID_TYPES":("RAID6","RAID5"),
                                  "NUM_DATA_DRIVES":(4,4),
                                  "NUM_SPARE":(2,2),
                                  "AUTO_CREATE":(True,True),
                                  "ARRAY_MOUNT":("WT","WT")}}
TESTCASES1 = [
    "SPS_4638","SPS_4641","SPS_4642","SPS_4643","SPS_4647","SPS_4649","SPS_4650","SPS_4651"
]
@pytest.mark.parametrize("testcase",TESTCASES1)
def test_nft_quick_rebuild_with_por(array_fixture,testcase):
    try:
        pos = array_fixture

        assert create_array_and_volumes(pos=pos,testcase=testcase,num_array=len(TESTCASE_LIST[testcase]["ARRAYS"]["RAID_TYPES"])) == True

        nvme_devs = nvme_connect(pos=pos)[1]

        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=50 --verify=md5"

        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                      fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("*************** Sleep for 5 min ***************")
        time.sleep(10)

        array = list(pos.cli.array_dict.keys())[0]
        if testcase == "SPS_4651":

            for array in list(pos.cli.array_dict.keys()):

                assert trigger_quick_rebuild(pos=pos,array=array) == True

                assert pos.target_utils.array_rebuild_wait(array_name=array) == True

                assert array_disks_hot_remove(pos=pos, array_name=array, disk_remove_interval_list=[(100,)]) == True

                assert pos.target_utils.array_rebuild_wait(array_name=array) == True
        else:
            #Do quick rebuild multiple iteration
            for iter in range(TESTCASE_LIST[testcase]["QUICK_REBUILD"]):

                assert trigger_quick_rebuild(pos=pos,array=array) == True

                assert pos.target_utils.array_rebuild_wait(array_name=array) == True

            assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True

            if "POR" in list(TESTCASE_LIST[testcase].keys()):

                for por in TESTCASE_LIST[testcase]["POR"]:

                    if TESTCASE_LIST[testcase]["POR"] == "SPOR":

                        assert pos.target_utils.Spor(uram_backup=False,write_through=True) == True

                    else:

                        assert pos.target_utils.Npor() == True

        out, async_io = pos.client.fio_generic_runner(nvme_devs,fio_user_data=fio_cmd, run_async=True)

        assert out == True

        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")

        pos.exit_handler(expected=False)


