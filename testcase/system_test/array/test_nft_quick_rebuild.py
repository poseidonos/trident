from common_libs import *
import logger
logger = logger.get_logger(__name__)
import random


def create_array_and_volumes(pos, raid_types, data_disks, spare_disks, num_array=None):
    assert multi_array_data_setup(data_dict=pos.data_dict, num_array=num_array,
                                  raid_types=raid_types,
                                  num_data_disks=data_disks,
                                  num_spare_disk=spare_disks,
                                  auto_create=(True, True),
                                  array_mount=("WT", "WT")) == True

    assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True

    assert pos.cli.list_array()[0] == True

    assert pos.target_utils.get_subsystems_list() == True

    assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=pos.cli.array_dict.keys(),
                                            subs_list=pos.target_utils.ss_temp_list) == True
    return True

def trigger_quick_rebuild(pos,array):
    # Replace data drive of the first array

    assert pos.cli.array_info(array_name=array)[0] == True

    data_dev = random.choice(list(pos.cli.array_info[array]['data_list']))

    logger.info("*************** Triggering device replacement ***************")

    assert pos.cli.array_replace_disk(array_name=array, device_name=data_dev)[0] == True

    return True

TESTCASE_DICT={}
TESTCASE_DICT["T0"] = {"raid_types":("RAID5","RAID6"), "spare_disks":(2,2), "situation": ("REBUILDING","REBUILDING")}
TESTCASE_DICT["T1"] = {"raid_types":("RAID10","RAID5"), "spare_disks":(2,2), "situation":("REBUILDING","REBUILDING")}
TESTCASE_DICT["T2"] = {"raid_types":("RAID6","RAID5"), "spare_disks":(2,0), "situation":("REBUILDING","DEGRADED")}
TESTCASE_DICT["T3"] = {"raid_types":("RAID10","RAID5"), "spare_disks":(2,0), "situation":("REBUILDING","DEGRADED")}
TESTCASES = [
    "T0","T1","T2","T3"
]
@pytest.mark.parametrize("testcase",TESTCASES)
def test_nft_quick_rebuild_while_io_running(array_fixture,testcase):
    try:
        pos = array_fixture
        assert create_array_and_volumes(pos=pos, data_disks=(4, 4),
                                        raid_types=TESTCASE_DICT[testcase]["raid_types"],
                                        spare_disks=TESTCASE_DICT[testcase]["spare_disks"],
                                        num_array=2) == True

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
        assert pos.cli.array_info(array_name=arrays[0])[0] == True
        assert pos.cli.array_info[arrays[0]]['situation'] ==  TESTCASE_DICT[testcase]["situation"][0]

        #Hot remove the data drive of second array
        assert array_disks_hot_remove(pos=pos, array_name=arrays[1], disk_remove_interval_list=[(0,)]) == True
        assert pos.cli.array_info(array_name=arrays[1])[0] == True
        assert pos.cli.array_info[arrays[1]]['situation'] == TESTCASE_DICT[testcase]["situation"][1]

        #Wait for rebuild to complete
        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True

        assert pos.target_utils.array_rebuild_wait_multiple(array_list=arrays) == True

        for array in arrays:
            assert pos.cli.array_info(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")

        pos.exit_handler(expected=False)



TESTCASE_DICT["T4"] = {"raid_types":("RAID6",),"spare_disks":(2,), "quick_rebuild":2, "por":["SPOR"]}
TESTCASE_DICT["T5"] = {"raid_types":("RAID10",),"spare_disks":(2,), "quick_rebuild":2, "por":["SPOR"]}
TESTCASE_DICT["T6"] = {"raid_types":("RAID6",),"spare_disks":(2,), "quick_rebuild":2, "por":["NPOR"]}
TESTCASE_DICT["T7"] = {"raid_types":("RAID10",),"spare_disks":(2,), "quick_rebuild":2, "por":["NPOR"]}
TESTCASE_DICT["T8"] = {"raid_types":("RAID5",),"spare_disks":(3,), "quick_rebuild":3, "por":["NPOR","SPOR"]}
TESTCASE_DICT["T9"] = {"raid_types":("RAID6",),"spare_disks":(3,), "quick_rebuild":3, "por":["NPOR","SPOR"]}
TESTCASE_DICT["T10"] = {"raid_types":("RAID6",),"spare_disks":(2,), "quick_rebuild":2}
TESTCASE_DICT["T11"] = {"raid_types":("RAID6","RAID5"),"spare_disks":(2,2)}
TESTCASES1 = [
    "T4","T5","T6","T7","T8","T9","T10","T11"
]
@pytest.mark.parametrize("testcase",TESTCASES1)
def test_nft_quick_rebuild_with_por(array_fixture,testcase):
    try:
        pos = array_fixture

        assert create_array_and_volumes(pos=pos, data_disks=(4,4),raid_types=TESTCASE_DICT[testcase]["raid_types"],
                                        spare_disks=TESTCASE_DICT[testcase]["spare_disks"],
                                        num_array=len(TESTCASE_DICT[testcase]["raid_types"])) == True

        #Initiate IO
        nvme_devs = nvme_connect(pos=pos)[1]
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=50 --verify=md5"
        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                      fio_user_data=fio_cmd, run_async=True)
        assert out == True

        logger.info("*************** Sleep for 5 min ***************")
        time.sleep(300)

        array = list(pos.cli.array_dict.keys())[0]
        if testcase == "T11":
            for array in list(pos.cli.array_dict.keys()):
                assert trigger_quick_rebuild(pos=pos,array=array) == True
                assert pos.target_utils.array_rebuild_wait(array_name=array) == True
                assert array_disks_hot_remove(pos=pos, array_name=array, disk_remove_interval_list=[(100,)]) == True
                assert pos.target_utils.array_rebuild_wait(array_name=array) == True
        else:
            #Do quick rebuild multiple iteration
            for iter in range(TESTCASE_DICT[testcase]["quick_rebuild"]):
                assert trigger_quick_rebuild(pos=pos,array=array) == True
                assert pos.target_utils.array_rebuild_wait(array_name=array) == True

            assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True

            #Triggering POR sequence(NPOR/SPOR)
            if "POR" in list(TESTCASE_DICT[testcase].keys()):
                for por in TESTCASE_DICT[testcase]["por"]:
                    if TESTCASE_DICT[testcase]["POR"] == "SPOR":
                        assert pos.target_utils.Spor(uram_backup=False,write_through=True) == True
                    else:
                        assert pos.target_utils.Npor() == True

        #Run IO on the volumes
        out, async_io = pos.client.fio_generic_runner(nvme_devs,fio_user_data=fio_cmd, run_async=True)
        assert out == True

        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")

        pos.exit_handler(expected=False)


