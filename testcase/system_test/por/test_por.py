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


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict, data_store, iomode
    pos = POS()
    data_store = {}
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    # assert pos.cli.reset_devel()[0] == True

    yield pos


def teardown_function():

    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True

    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            # assert pos.cli.wbt_flush(array_name=array)[0] == True ## for code coverage
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    assert pos.cli.reset_devel()[0] == True
    assert pos.target_utils.pci_rescan() == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


def nvme_connect():
    assert pos.target_utils.get_subsystems_list() == True
    for nqn in pos.target_utils.ss_temp_list:
        assert pos.client.nvme_connect(nqn, pos.target_utils.helper.ip_addr[0], "1158")
    assert pos.client.nvme_list() == True
    return True


def mount_fs():
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


def unmount_fs(iomode):
    if iomode == False:
        assert pos.client.unmount_FS(mount_pts) == True


def do_SPOR(wt=False, expected=True, uram_backup=True):

    assert pos.target_utils.Spor(uram_backup=uram_backup, write_through=wt) == expected


def do_Npor():
    assert pos.target_utils.Npor() == True


def runFIO(io_mode, device_list, ops):
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


@pytest.mark.parametrize("writeback", [True])
@pytest.mark.parametrize("numvol", [1])
@pytest.mark.parametrize("iomode", [True, False])
@pytest.mark.parametrize("numarray", [2])
@pytest.mark.parametrize("spor", [False])
def test_por(writeback, numvol, numarray, iomode, spor):
    try:
        por_dict = data_dict
        por_dict["system"]["phase"] = "false"
        por_dict["device"]["phase"] = "false"
        por_dict["subsystem"]["phase"] = "false"

        por_dict["array"]["phase"] = "true"
        por_dict["volume"]["phase"] = "true"

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
        nvme_connect()
        if iomode == False:
            mount_fs()
            runFIO(iomode, mount_pts, "write")
        else:
            runFIO(iomode, pos.client.nvme_list_out, "write")
        if spor == True:
            do_SPOR()
        else:
            do_Npor()
        if iomode == False:
            mount_fs()
            runFIO(iomode, mount_pts, "read")
        else:
            runFIO(iomode, pos.client.nvme_list_out, "read")

        unmount_fs(iomode)
    except Exception as e:
        logger.error(e)
        unmount_fs(iomode)
        assert 0


def test_random_por():
    try:
        por_dict = data_dict
        por_dict["system"]["phase"] = "false"
        por_dict["device"]["phase"] = "false"
        por_dict["subsystem"]["phase"] = "false"

        por_dict["array"]["phase"] = "true"
        por_dict["volume"]["phase"] = "true"
        assert pos.target_utils.pos_bring_up(data_dict=por_dict) == True
        nvme_connect()
        start_time = time.time()
        end_time = start_time + (60 * runtime)
        logger.info("RunTime is {} minutes".format(runtime))
        runFIO(io_mode=True, device_list=pos.client.nvme_list_out, ops="write")
        while True:
            por = ["SPOR", "NPOR"]
            porChoice = random.choice(por)
            do_Npor() if porChoice == "NPOR" else do_SPOR()
            runFIO(io_mode=True, device_list=pos.client.nvme_list_out, ops="read")
            if time.time() > end_time:
                logger.info("runtime completed")
                break
            time_left = int((end_time - time.time()) / 60)
            logger.info(
                f"Remaining time for the test to be completed is {str(time_left)} minutes"
            )

    except Exception as e:
        logger.error(e)
        assert 0
