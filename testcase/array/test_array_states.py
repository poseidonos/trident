import pytest
import time
import random
import os
import json
from common_libs import *

# sys.path.insert(0, '../')
# sys.path.insert(0, '/root/poseidon/ibot')
import logger as logger

from pos import POS
from array_state import _Array as array

logger = logger.get_logger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/config.json".format(dir_path)) as f:
    config_dict = json.load(f)


def pos_setup(pos, num_array, list_array_obj, data_dict):
    
    
    data_dict["array"]["num_array"] = 2 if num_array == 2 else 1
    assert pos.target_utils.bringupArray(data_dict = data_dict) == True
    assert pos.target_utils.bringupVolume(data_dict = data_dict) == True
    assert pos.cli.array_list()[0] == True
    assert pos.target_utils.get_subsystems_list() == True

    array_list = list(pos.cli.array_dict.keys())
    for item in range(len(array_list)):
        list_array_obj.append(
            array(pos,
                array_name=array_list[item],
                data_dict=data_dict,
                cli_history=pos.cli.cli_history,
            )
        )
        list_array_obj[item].subsystem = pos.target_utils.ss_temp_list
        list_array_obj[item].func["param"]["pre_write"] = True


@pytest.mark.parametrize("num_array", [1, 2])
def test_array_states(array_fixture,num_array):
    try:
        fio_command = "fio --ioengine=libaio --rw=write --bs=16384 --iodepth=256 --direct=0  --numjobs=1 --verify=pattern --verify_pattern=0x0c60df8108c141f6 --do_verify=1 --verify_dump=1 --verify_fatal=1 --group_reporting --log_offset=1 --size=100% --name=pos0 "
        pos = array_fixture
        list_array_obj = []
        # step ::0 : variable initialization
        data_dict = pos.data_dict
        loop = 1
        # seed = 10
        seed = random.randint(1, 10)
        random.seed(seed)
        logger.info(
            "#################################################################################################"
        )
        logger.info(
            "--------------------------------------- RANDOM SEED : {} ---------------------------------------".format(
                seed
            )
        )
        logger.info(
            "#################################################################################################"
        )
        pos_setup(pos, num_array, list_array_obj, data_dict)
        # step ::1 : setup envirenment for POS

        # step ::2 : time setup
        start_time = time.time()
        run_time = int(config_dict["test_ArrayStates"]["runtime"])
        end_time = start_time + (60 * run_time)
        logger.info("RunTime is {} minutes".format(run_time))

        # step ::3 : run fio
        run_io(pos, fio_command=fio_command)

        while True:
            logger.info(
                "#################################################################################################"
            )
            logger.info(
                "---------------------------------------- LOOP COUNT : {} ----------------------------------------".format(
                    loop
                )
            )
            logger.info(
                "#################################################################################################"
            )
            # step ::4 : select randomly the functions to be executed next and run
            for array_obj in list_array_obj:
                assert array_obj.select_next_state() == True
                assert array_obj.run_func(list_array_obj=list_array_obj) == True
                time.sleep(2)
            # step ::5 : verify that the array state has changed to the expected value
            for array_obj in list_array_obj:
                assert array_obj.check_next_state() == True
            # step ::6 : check the path executed and add the function to command history

            for array_obj in list_array_obj:
                assert array_obj.cmd_history(loop=loop) == True
            # step ::7 : check the runtime and system memory
            if loop % 10 == 1:
                # assert pos.client.check_system_memory() == True
                assert pos.target_utils.helper.check_system_memory() == True
            if time.time() > end_time:
                for array_obj in list_array_obj:
                    assert array_obj.cmd_history(exit=True) == True

                break
            time_left = int((end_time - time.time()) / 60)
            logger.info(
                f"Remaining time for the test to be completed is {str(time_left)} minutes"
            )
            loop += 1
            time.sleep(2)

        pos.exit_handler(expected=True)
    except Exception as e:
        if len(list_array_obj) > 0:
            for array_obj in list_array_obj:
                assert array_obj.cmd_history(exit=False) == True

        pos.exit_handler(expected=False)
        assert 0
