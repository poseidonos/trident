import pytest, sys, json, os, shutil
import uuid
import traceback
from time import sleep

from datetime import datetime

from requests import session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
import logger as logging
from tags import EnvTags

logger = logging.get_logger(__name__)
from pos import POS
from utils import Client
from _pytest.runner import runtestprotocol

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../utils")))
from cce_tool import CodeCoverage 

global pos, method_name
dir_path = os.path.dirname(os.path.realpath(__file__))

# Read Trident config files 
trident_config_file = f"{dir_path}/config_files/trident_config.json"
with open(trident_config_file) as f:
    trident_config_data = json.load(f)

# Read static Json for config related info
with open("{}/config_files/static.json".format(dir_path)) as f:
    static_dict = json.load(f)

# Read Topology json fo
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
    logger.info("Test Session Start Time : {}".format(
                 session_start_time.strftime("%m/%d/%Y, %H:%M:%S")))

    # Initialize POS object
    global pos
    pos = POS()

    if trident_config_data["code_coverage"]["enable"] == "true":
        global cc
        cce_config_file = trident_config_data["code_coverage"]["config_file"]
        cc = CodeCoverage(cce_config_file)
        assert cc.target_init() == True
        assert cc.databse_init() == True

def get_code_coverage_data(jira_id):
    if not cc.get_code_coverage(jira_id):
        logger.error("Failed to get the code coverage")
        return False
    
    if not cc.parse_coverage_report(jira_id):
        logger.error("Failed to parser the code coverage report")
        return False

    if not cc.save_coverage_report(jira_id):
        logger.error("Failed to save the code coverage report")
        return False

    return True
   
@pytest.fixture(scope="function")
def array_fixture():
    logger.info("========== SETUP BEFORE TEST =========")
    start_time = datetime.now()
    logger.info("Test Session Start Time : {}".format(
                 start_time.strftime("%m/%d/%Y, %H:%M:%S")))

    assert check_pos_and_bringup() == True

    yield pos

    logger.info("========== CLEANUP AFTER TEST ==========")

    is_pos_running = False
    if pos.target_utils.helper.check_pos_exit() == False:
        is_pos_running = True

    assert client_teardown(is_pos_running) == True
    assert target_teardown(is_pos_running) == True
    
    end_time = datetime.now()
    logger.info("Test Session End Time : {}".format(
                 end_time.strftime("%m/%d/%Y, %H:%M:%S")))

    session_time = end_time - start_time
    session_minutes = divmod(session_time.seconds, 60)
    logger.info("Total Test Session Time : {} minutes {} seconds".format(
                 session_minutes[0], session_minutes[1]))

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
            assert pos.target_utils.get_subsystems_list() == True
            array_cleanup()
        else:
            logger.info("pos is already running")
            array_cleanup()
            
        return True
    except Exception as e:
        logger.error(e)
        traceback.print_exc()
        return False

def client_teardown(is_pos_running: bool) -> bool:
    """ Teardown function reset client """
    pos.client.reset(pos_run_status=is_pos_running) 
    return True

def target_teardown(is_pos_running: bool): 
    """ Teardown function to reset target """
    assert pos.target_utils.helper.check_system_memory() == True
    if is_pos_running:
        array_cleanup()
    assert pos.target_utils.re_scan() == True
    return True

def array_cleanup():
    assert pos.cli.array_list()[0] == True
    for array in list(pos.cli.array_dict.keys()):
        assert pos.cli.array_info(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True
    
    assert pos.cli.devel_resetmbr()[0] == True


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
    sleep(3)
    logger.info("################### Start Tag - System Info #####################")
    for key, value in invent.items():
        value.update({"IP": str(key)})
        value.move_to_end("IP", last=False)
        logger.info("Test Config :" + str(dict(value)))
    logger.info("################### End Tag - System Info #####################")

def pos_logs_core_dump(report, issuekey):
    time_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_key = f"{issuekey}_{time_stamp}"
    if (report.when == 'call' and report.outcome == 'failed'):
        #TODO update pos path

        if trident_config_data["dump_pos_core"]["enable"] == "true":
            #assert pos.target_utils.dump_core() == True
            #assert pos.target_utils.copy_core(unique_key) == True
            pass

        if trident_config_data["copy_pos_log"]["test_fail"] == "true":
            assert pos.target_utils.copy_pos_log(unique_key) == True

    elif (report.when == 'call' and report.outcome == 'passed' and
        trident_config_data["copy_pos_log"]["test_pass"] == "true"):
            assert pos.target_utils.copy_pos_log(unique_key) == True
    return True


@pytest.hookimpl(tryfirst=False, hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    global method_name
    driver = item.nodeid.split("::")[0]
    method = item.nodeid.split("::")[1]
    method_name = method
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

    if (trident_config_data["code_coverage"]["enable"] == "true" 
        and trident_config_data["code_coverage"]["scope"] == "function"):
        if issuekey == "No mapping found":
            issuekey = "No_Mapping"
        get_code_coverage_data(issuekey)

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

    global method_name
    if not pos_logs_core_dump(report, method_name):
        logger.error("Failed to generate and save the core dump")

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    log_path = logging.get_logpath()
    config.option.htmlpath = log_path + "/report.html"
    config.option.self_contained_html = True



def pytest_sessionfinish(session):
    session_end_time = datetime.now()
    log_path = logging.get_logpath()
    logger.info("Test Session End Time : {}".format(
                session_end_time.strftime("%m/%d/%Y, %H:%M:%S")))

    session_time = session_end_time - session_start_time
    session_minutes = divmod(session_time.seconds, 60)
    logger.info("Total Session Time : {} minutes {} seconds".format(
                 session_minutes[0], session_minutes[1]))

    logger.info(f"Logs and Html report for executed TCs are present in {log_path}")
    copy_dir(log_path)
    try:
        if pos:
            if pos.target_utils.helper.check_pos_exit() == False:
                pos.cli.pos_stop(grace_shutdown = False)
            pos._clearall_objects()
    except NameError:
        return "Exiting"
    
    if (trident_config_data["code_coverage"]["enable"] == "true" 
        and trident_config_data["code_coverage"]["scope"] == "session"):

        issuekey = trident_config_data["issue_key"]
        get_code_coverage_data(issuekey)

    logger.info("\n")


