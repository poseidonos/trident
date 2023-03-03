from pos import POS
import logger
import random

import pytest
import json
import os
import time

logger = logger.get_logger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/config.json".format(dir_path)) as f:
    config_dict = json.load(f)

runtime = config_dict["runtime"]
fio_commandLine = config_dict["fio_user_data"]
fio_pattern = config_dict["pattern"]
fio_runtime = config_dict["fio_runtime"]

def nvme_connect(pos):
    assert pos.target_utils.get_subsystems_list() == True
    for nqn in pos.target_utils.ss_temp_list:
        assert pos.client.nvme_connect(nqn, pos.target_utils.helper.ip_addr[0], "1158")
    assert pos.client.nvme_list() == True
    return True


def mount_fs(pos):
    try:
        global mount_pts
        assert pos.client.nvme_list() == True
        assert pos.client.create_File_system(pos.client.nvme_list_out) == True
        mount_out = pos.client.mount_FS(pos.client.nvme_list_out)
        if mount_out[0] == True:
            mount_pts = mount_out[1]
        else:
            raise Exception("mount failed")
        return True
    except Exception as e:
        logger.error(e)
        assert 0


def unmount_fs(pos, iomode):
    if iomode == False:
        assert pos.client.unmount_FS(mount_pts) == True


def do_SPOR(pos, wt=False, expected=True, uram_backup=True):

    assert pos.target_utils.spor(uram_backup=uram_backup, write_through=wt) == expected


def do_Npor(pos):
    assert pos.target_utils.npor() == True


def runFIO(pos, io_mode, device_list, ops):
    fio_write_line = fio_commandLine.format(ops, fio_pattern)
    if io_mode == True:
        assert (
            pos.client.fio_generic_runner(
                device_list, fio_user_data=fio_write_line, IO_mode=io_mode
            )[0]
            == True
        )
    else:
        assert pos.client.fio_generic_runner(device_list, IO_mode=io_mode)[0] == True

def set_pos_data_dict(data_dict):
    data_dict["system"]["phase"] = "true"
    data_dict["device"]["phase"] = "true"
    data_dict["subsystem"]["phase"] = "true"
    data_dict["array"]["phase"] = "true"
    data_dict["volume"]["phase"] = "true"

@pytest.mark.parametrize("writeback", [True])
@pytest.mark.parametrize("numvol", [1,256])
@pytest.mark.parametrize("iomode", [True, False])
@pytest.mark.parametrize("numarray", [2])
@pytest.mark.parametrize("spor", [True,False])
def test_por(system_fixture, writeback, numvol, numarray, iomode, spor):
    try:
        pos = system_fixture
        por_dict = pos.data_dict
        set_pos_data_dict(por_dict)

        por_dict["array"]["numarray"] = numarray
        (
            por_dict["array"]["pos_array"][0]["write_back"],
            por_dict["array"]["pos_array"][1]["write_back"],
        ) = (writeback, writeback)
        (
            por_dict["volume"]["pos_volumes"][0]["num_vol"],
            por_dict["volume"]["pos_volumes"][1]["num_vol"],
        ) = (numvol, numvol)
        assert pos.target_utils.pos_bring_up(data_dict=por_dict) == True
        nvme_connect(pos)
        if iomode == False:
            mount_fs(pos)
            runFIO(pos, iomode, mount_pts, "write")
        else:
            runFIO(pos, iomode, pos.client.nvme_list_out, "write")
        if spor == True:
            do_SPOR(pos)
        else:
            do_Npor(pos)
        if iomode == False:
            mount_fs(pos)
            runFIO(pos, iomode, mount_pts, "read")
        else:
            runFIO(pos, iomode, pos.client.nvme_list_out, "read")

        unmount_fs(pos, iomode)
    except Exception as e:
        logger.error(e)
        try:
            unmount_fs(pos, iomode)
        except:
            pass
        pos.exit_handler(expected=False)


def test_random_por(system_fixture):
    try:
        pos = system_fixture
        por_dict = pos.data_dict
        set_pos_data_dict(por_dict)
        assert pos.target_utils.pos_bring_up(data_dict=por_dict) == True
        nvme_connect(pos)
        start_time = time.time()
        end_time = start_time + (60 * runtime)
        logger.info("RunTime is {} minutes".format(runtime))
        runFIO(pos, io_mode=True, device_list=pos.client.nvme_list_out, ops="write")
        while True:
            por = ["SPOR", "NPOR"]
            porChoice = random.choice(por)
            do_Npor(pos) if porChoice == "NPOR" else do_SPOR(pos)
            runFIO(pos, io_mode=True, device_list=pos.client.nvme_list_out, ops="read")
            if time.time() > end_time:
                logger.info("runtime completed")
                break
            time_left = int((end_time - time.time()) / 60)
            logger.info(
                f"Remaining time for the test to be completed is {str(time_left)} minutes"
            )

    except Exception as e:
        logger.error(e)
        pos.exit_handler(expected=False)
