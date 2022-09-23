#
#    BSD LICENSE
#    Copyright (c) 2021 Samsung Electronics Corporation
#    All rights reserved.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions
#    are met:
#
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in
#        the documentation and/or other materials provided with the
#        distribution.
#      * Neither the name of Samsung Electronics Corporation nor the names of
#        its contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import pytest, sys, json, os, shutil
import uuid
import traceback

from datetime import datetime

from requests import session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
import logger as logging
from tags import EnvTags

logger = logging.get_logger(__name__)
from pos import POS
from utils import Client
from _pytest.runner import runtestprotocol

global pos
dir_path = os.path.dirname(os.path.realpath(__file__))

trident_config_file = f"{dir_path}/config_files/trident_config.json"
with open(trident_config_file) as f:
    trident_config_data = json.load(f)

with open("{}/config_files/static.json".format(dir_path)) as f:
    static_dict = json.load(f)
login = []
with open("{}/config_files/topology.json".format(dir_path)) as f:
    config_dict = json.load(f)
login = config_dict["login"]["initiator"]["client"]
login.append(config_dict["login"]["target"]["server"][0])
with open("{}/config_files/trident_mapping.json".format(dir_path)) as f:
    mapping_dict = json.load(f)


def make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def copy_dir(source_item):
    path_list = source_item.split("/")
    if os.path.isdir(source_item):
        destination_item = "/root/cdc/{}".format(path_list[-1])
        make_dir(destination_item)
        sub_items = os.listdir(source_item)
        for sub_item in sub_items:
            full_file_name = os.path.join(source_item, sub_item)
            Full_destination_item = os.path.join(destination_item, sub_item)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, Full_destination_item)


def pytest_sessionstart(session):
    global session_start_time
    session_start_time = datetime.now()
    logger.info(
        "Test Session Start Time : {}".format(
            session_start_time.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )

   
@pytest.fixture(scope="module")
def setup_clenup_array_module():
    logger.info("========== SETUP ARRAY MODULE =========")
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    yield pos

    logger.info("========= CLEANUP ARRAY MODULE ========")
    pos.exit_handler(expected=True)


@pytest.fixture(scope="function")
def setup_cleanup_array_function(setup_clenup_array_module):
    logger.info("========== SETUP ARRAY TEST =========")
    pos = setup_clenup_array_module
    if pos.target_utils.helper.check_pos_exit() == True:
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
    data_dict = pos.data_dict
    data_dict["system"]["phase"] = "false"
    data_dict["device"]["phase"] = "false"
    data_dict["array"]["phase"] = "true"

    assert pos.cli.list_device()[0] == True
    logger.info(f"System Disk : {pos.cli.system_disks}")

    yield pos

    logger.info("========== CLEANUP ARRAY TEST =========")
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    for array in pos.cli.array_dict.keys():
        assert pos.cli.info_array(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.delete_array(array_name=array)[0] == True

    logger.info("==========================================")


# @pytest.fixture(scope="session", autouse=True)
def setup_cleanup():
    global pos
    session_start_time = datetime.now()
    logger.info(
        "Test Session Start Time : {}".format(
            session_start_time.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )
    # Start POS, Device Scan and Create Transport
    pos = POS()
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    # Reset the Disk MBR
    assert pos.cli.reset_devel()[0] == True

    yield pos

    # Stop POS
    pos.exit_handler(expected=True)

    session_end_time = datetime.now()
    logger.info(
        "Test Session End Time : {}".format(
            session_end_time.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )
    session_time = session_end_time - session_start_time
    session_minutes = divmod(session_time.seconds, 60)
    logger.info(
        "Total Session Time : {} minutes {} seconds".format(
            session_minutes[0], session_minutes[1]
        )
    )


@pytest.fixture(scope="function")
def array_setup_cleanup():
    logger.info("========== SETUP BEFORE TEST =========")

    # Disable the POS system start and Device Scan Phase
    data_dict = pos.data_dict
    data_dict["system"]["phase"] = "false"
    data_dict["device"]["phase"] = "false"
    data_dict["array"]["phase"] = "true"

    assert pos.cli.list_device()[0] == True
    logger.info(f"System Disk : {pos.cli.system_disks}")
    yield pos

    logger.info("========== CLEANUP AFTER TEST =========")
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    for array in pos.cli.array_dict.keys():
        assert pos.cli.info_array(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.delete_array(array_name=array)[0] == True

    logger.info("==========================================")


################################################################################################################


def check_pos_and_bringup():
    try:

        pos.data_dict["system"]["phase"] = "true"
        pos.data_dict["subsystem"]["phase"] = "true"
        pos.data_dict["device"]["phase"] = "true"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.bringupSystem(data_dict=pos.data_dict) == True
            assert pos.target_utils.bringupDevice(data_dict=pos.data_dict) == True
            assert pos.target_utils.bringupSubsystem(data_dict=pos.data_dict) == True
            assert pos.cli.reset_devel()[0] == True
            assert pos.target_utils.get_subsystems_list() == True
        else:
            logger.info("pos is already running")
            array_cleanup()
        return True
    except Exception as e:
        logger.error(e)
        traceback.print_exc()
        return False


def unmount_fs() -> bool:
    """if mounted to FS delete FS then disconnect"""
    if len(list(pos.client.mount_point.keys())) > 0:
        for dir in list(pos.client.mount_point.values()):
            if pos.client.is_dir_present(dir_path=dir) == True:
                assert pos.client.unmount_FS(fs_mount_pt=[dir]) == True
    return True


def client_tear_down() -> bool:
    """check if nvme controller is present if yes disconnect"""

    if pos.client.ctrlr_list()[1] is not None:

        assert unmount_fs() == True
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True
    return True


def array_tear_down_function():
    
    assert pos.target_utils.helper.check_system_memory() == True
    
    if pos.target_utils.helper.check_pos_exit() == False:
        assert array_cleanup() ==True 
        assert pos.target_utils.pci_rescan() == True
        
    return True
def array_cleanup():
        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        if len(array_list) == 0:
            logger.info("No array found in the config")
        else:
            for array in array_list:
                assert pos.cli.info_array(array_name=array)[0] == True
                if pos.cli.array_dict[array].lower() == "mounted":
                    assert volume_cleanup(array) == True
                    assert pos.cli.unmount_array(array_name=array)[0] == True
            assert pos.cli.reset_devel()[0] == True
        return True
def volume_cleanup(array_name):
    assert pos.cli.list_volume(array_name = array_name)[0] == True
    if len(pos.cli.vols) > 0:
        assert pos.target_utils.deleteAllVolumes(arrayname = array_name) == True
    return True


@pytest.fixture(scope="function")
def array_fixture():
    session_start_time = datetime.now()
    logger.info(
        "Test Session Start Time : {}".format(
            session_start_time.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )
    logger.info("========== SETUP BEFORE TEST =========")
    assert check_pos_and_bringup() == True
    yield pos
    logger.info("========== CLEANUP AFTER TEST ==========")
    assert client_tear_down() == True
    assert array_tear_down_function() == True
    
    session_end_time = datetime.now()
    logger.info(
        "Test Session End Time : {}".format(
            session_end_time.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )
    session_time = session_end_time - session_start_time
    session_minutes = divmod(session_time.seconds, 60)
    logger.info(
        "Total Session Time : {} minutes {} seconds".format(
            session_minutes[0], session_minutes[1]
        )
    )


def teardown_session():
    logger.info("============= CLEANUP SESSION AFER TEST")
    pos.exit_handler(expected=False)


#################################################################################################################
def tags_info(target_ip, method, start_time, driver, issuekey):
    logger.info("################### Start Tag - Test Info ###################")
    logger.info(
        "TC Unique ID : {}_{}_{}_{}".format(
            str(uuid.uuid4()),
            target_ip,
            method,
            (start_time.strftime("%m_%d_%Y_%H_%M_%S")),
        )
    )

    for key in static_dict["Project Info"]:
        logger.info(key + " : " + str(static_dict["Project Info"][key]))
    for key in static_dict["Test Cycle Info"]:
        logger.info(key + " : " + str(static_dict["Test Cycle Info"][key]))
    logger.info("Test Case Driver File Name : " + driver)
    logger.info("Test Case Name : " + method)
    logger.info("JIRA_TC_ID : " + issuekey)
    logger.info("################### End Tag - Test Info #####################")
    invent = {}
    for item in login:
        node = [str(item["ip"]), str(item["username"]), str(item["password"])]
        tag = EnvTags(node, item["ip"], item["username"], item["password"])
        out = tag.get_tags()
        if out:
            logger.info("Tags received for the node :  {}".format(node[0]))
            invent[item["ip"]] = tag.inv
        else:
            logger.error("No tags received from the node : {}".format(node[0]))
            assert 0
    logger.info("################### Start Tag - System Info #####################")
    for key, value in invent.items():
        value.update({"IP": str(key)})
        value.move_to_end("IP", last=False)
        logger.info("Test Config :" + str(dict(value)))
    logger.info("################### End Tag - System Info #####################")
    global pos
    pos = POS()


def pos_logs_core_dump(item, nextitem, issuekey):
    time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_key = f"{issuekey}_{time_stamp}"
    reports = runtestprotocol(item, nextitem=nextitem, log=False)
    for report in reports:
        if report.when == "call" and report.outcome == "failed":
            if trident_config_data["dump_pos_core"]["enable"] == "true":
                assert pos.target_utils.dump_core() == True
                assert pos.target_utils.copy_core(unique_key) == True

            if trident_config_data["copy_pos_log"]["test_fail"] == "true":
                assert pos.target_utils.copy_pos_log(unique_key) == True

        elif (
            report.when == "call"
            and report.outcome == "passed"
            and trident_config_data["copy_pos_log"]["test_pass"] == "true"
        ):
            assert pos.target_utils.copy_pos_log(unique_key) == True
    return True


@pytest.hookimpl(tryfirst=False, hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):

    driver = item.nodeid.split("::")[0]
    method = item.nodeid.split("::")[1]
    try:
        issuekey = mapping_dict[method]
    except:
        issuekey = "No mapping found"
    logger.info(
        "======================== START OF {} ========================".format(method)
    )
    start_time = datetime.now()
    logger.info("Start Time : {}".format(start_time.strftime("%m/%d/%Y, %H:%M:%S")))

    target_ip = login[-1]["ip"]

    if trident_config_data["elk_log_stage"]["enable"] == "true":
        tags_info(target_ip, method, start_time, driver, issuekey)

    yield

    end_time = datetime.now()
    logger.info("End Time : {}".format(end_time.strftime("%m/%d/%Y, %H:%M:%S")))
    execution_time = end_time - start_time
    execution_minutes = divmod(execution_time.seconds, 60)
    logger.info(
        "Execution Time : {} minutes {} seconds".format(
            execution_minutes[0], execution_minutes[1]
        )
    )

    if not pos_logs_core_dump(item, nextitem, method):
        logger.error("Failed to generate and save the core dump")

    logger.info(
        "======================== END OF {} ========================\n".format(method)
    )


def pytest_runtest_logreport(report):
    log_status = "======================== Test Status : {} ========================"
    if report.when == "setup":
        setup_status = report.outcome
        if setup_status == "failed":
            logger.info(log_status.format("FAIL"))
        elif setup_status == "skipped":
            logger.info(log_status.format("SKIP"))
    if report.when == "call":
        test_status = report.outcome
        if test_status == "passed":
            logger.info(log_status.format("PASS"))
        elif test_status == "failed":
            logger.info(log_status.format("FAIL"))


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    log_path = logging.get_logpath()
    config.option.htmlpath = log_path + "/report.html"
    config.option.self_contained_html = True



def pytest_sessionfinish(session):
    session_end_time = datetime.now()
    log_path = logging.get_logpath()
    logger.info(
        "Test Session End Time : {}".format(
            session_end_time.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )
    session_time = session_end_time - session_start_time
    session_minutes = divmod(session_time.seconds, 60)
    logger.info(
        "Total Session Time : {} minutes {} seconds".format(
            session_minutes[0], session_minutes[1]
        )
    )
    logger.info(
        "Logs and Html report for executed TCs are present in {}".format(log_path)
    )
    copy_dir(log_path)
    try:
        if pos:
            if pos.target_utils.helper.check_pos_exit() == True:
                pos.cli.stop_system(grace_shutdown = False)
            pos._clearall_objects()
    except NameError:
        return "Exiting"
    logger.info("/n")


