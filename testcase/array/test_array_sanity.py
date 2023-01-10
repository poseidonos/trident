from array import array
import pytest
import random
from pos import POS
from common_libs import *
import json
import os
import time

dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/config.json".format(dir_path)) as f:
    config_dict = json.load(f)


import logger
logger = logger.get_logger(__name__)

raid = {
    "RAID0": {"spare": 0, "data": 2},
    "RAID10": {"spare": 2, "data": 2},
    "no-raid": {"spare": 0, "data": 1},
    "RAID5": {"spare": 1, "data": 3},
    "RAID6": {"spare": 2, "data": 4},
}


def array_ops(pos):
    arrayname = "array1"
    assert pos.cli.array_info(array_name=arrayname)[0] == True
    if pos.data_dict["array"]["pos_array"][0]["raid_type"] not in ["RAID0", "no-raid"]:
        disklist = [random.choice(pos.cli.dev_type["SSD"])]
        assert pos.target_utils.device_hot_remove(disklist) == True
        # assert pos.cli.array_unmount(array_name=arrayname)[0] == False
        # assert pos.cli.array_delete(array_name=array)[0] == False
        assert pos.target_utils.array_rebuild_wait(array_name=arrayname) == True

    assert pos.cli.device_scan()[0] == True
    assert pos.cli.array_info(array_name=arrayname)[0] == True

    assert pos.cli.array_unmount(array_name=arrayname)[0] == True
    assert pos.cli.array_delete(array_name=arrayname)[0] == True
    assert pos.cli.array_unmount(array_name="array2")[0] == True
    assert pos.cli.array_delete(array_name="array2")[0] == True
    assert pos.cli.array_list()[0] == True
    # assert pos.cli.telemetry_stop()[0] == True
    return True


def negative_tests(pos):
    assert pos.cli.device_list()[0] == True
    assert (
        pos.cli.array_autocreate(
            array_name="array2",
            num_data=raid[pos.data_dict["array"]["pos_array"][0]["raid_type"]]["data"],
            num_spare=raid[pos.data_dict["array"]["pos_array"][0]["raid_type"]][
                "spare"
            ],
            buffer_name=pos.cli.dev_type["NVRAM"][1],
            raid=random.choice(list(raid.keys())),
        )[0]
        == False
    )

    for array in ["array1", "array2"]:
        writechoice = random.choice([True, False])
        assert pos.cli.array_mount(array_name=array, write_back=writechoice)[0] == False
        assert pos.cli.array_delete(array_name=array)[0] == False
    return True


@pytest.mark.sanity
def test_SanityArray(array_fixture):
    try:
        start_time = time.time()
        run_time = int(config_dict["test_ArraySanity"]["runtime"])
        end_time = start_time + (60 * run_time)
        logger.info("RunTime is {} minutes".format(run_time))
        while True:

            pos = array_fixture

            pos.data_dict["array"]["pos_array"][0]["raid_type"] = random.choice(
                list(raid.keys())
            )
            pos.data_dict["array"]["pos_array"][1]["raid_type"] = random.choice(
                list(raid.keys())
            )
            pos.data_dict["array"]["pos_array"][0]["write_back"] = random.choice(
                [True, False]
            )
            pos.data_dict["array"]["pos_array"][1]["write_back"] = random.choice(
                [True, False]
            )
            pos.data_dict["array"]["pos_array"][0]["data_device"] = raid[
                pos.data_dict["array"]["pos_array"][0]["raid_type"]
            ]["data"]
            pos.data_dict["array"]["pos_array"][1]["data_device"] = raid[
                pos.data_dict["array"]["pos_array"][1]["raid_type"]
            ]["data"]
            pos.data_dict["array"]["pos_array"][0]["spare_device"] = raid[
                pos.data_dict["array"]["pos_array"][0]["raid_type"]
            ]["spare"]
            pos.data_dict["array"]["pos_array"][1]["spare_device"] = raid[
                pos.data_dict["array"]["pos_array"][1]["raid_type"]
            ]["spare"]
            pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = random.randint(
                1, 256
            )
            pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = random.randint(
                1, 256
            )
            por = random.choice([True])
            logger.info(pos.data_dict)
            assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
            assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
            run_io(pos)
            assert pos.cli.array_list()[0] == True
            array_name = list(pos.cli.array_dict.keys())[0]
            assert pos.cli.array_info(array_name=array_name)[0] == True
            if pos.data_dict["array"]["pos_array"][0]["raid_type"] not in [
                "RAID0",
                "no-raid",
            ]:
                assert (
                    pos.cli.array_addspare(
                        array_name=array_name,
                        device_name=pos.cli.array_data["array1"]["data_list"][0],
                    )[0]
                    == False
                )
                assert pos.cli.device_list()[0] == True
                assert (
                    pos.cli.array_addspare(
                        array_name=array_name, device_name=pos.cli.system_disks[0]
                    )[0]
                    == True
                )

            ## Create3rd array/ duplicate array

            negative_tests(pos)
            if por == True:
                logger.info("Performing SPOR")
                pos.target_utils.Spor()
            else:
                logger.info("Performing NPOR")
                pos.target_utils.Npor()

            array_ops(pos)
            if time.time() > end_time:
                logger.info("Test completed")
                break
            time_left = int((end_time - time.time()) / 60)
            logger.info(
                f"Remaining time for the test to be completed is {str(time_left)} minutes"
            )
            time.sleep(2)

    except Exception as e:

        assert 0


@pytest.mark.sanity
def test_Create_Array_alldrives(array_fixture):
    try:
        pos = array_fixture

        assert pos.cli.device_list()[0] == True

        # Minimum Required Uram = Num Of Disk * 128MB + 512MB
        # Uram size in calculated in MB
        uram_size = (int(pos.data_dict["device"]["uram"][0]["bufer_size"])
                    * int(pos.data_dict["device"]["uram"][0]["strip_size"]))
        if ((len(pos.cli.dev_type["SSD"]) * 128 + 512) < uram_size):
            pytest.skip("Minimum uram size requirement is not met")

        assert pos.cli.array_create(
                    array_name=pos.data_dict["array"]["pos_array"][0]["array_name"],
                    data=pos.cli.dev_type["SSD"],
                    write_buffer=pos.data_dict["device"]["uram"][0]["uram_name"],
                    raid_type="RAID5", spare=[])[0] == True

    except Exception as e:
        logger.error("Test case failed due to {e}")
        assert 0
