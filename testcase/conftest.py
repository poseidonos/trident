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

global pos, method_name #,i trident_config_data, static_dict, config_dict, mapping_dict


# Global Files 
dir_path = os.path.dirname(os.path.realpath(__file__))
trident_config_file = f"{dir_path}/config_files/trident_config.json"
static_config_file = f"{dir_path}/config_files/static.json"
topology_file = f"{dir_path}/config_files/topology.json"
trident_mapping_file = f"{dir_path}/config_files/trident_mapping.json"

def trident_test_init():
    """
    Tridnet Init Sequnce - To be called during each session start.
    """
    try:
        global trident_config_data, static_dict, config_dict, mapping_dict
        global login, pos
        logger.info("Trident Init Sequence Started...")

        logger.debug("Load Trident Config")
        with open(trident_config_file) as f:
            trident_config_data = json.load(f)

        logger.debug("Load Trident Static Config")
        with open(static_config_file) as f:
            static_dict = json.load(f)
        
        logger.debug("Load Topology Information")
        with open(topology_file) as f:
            config_dict = json.load(f)

        logger.debug("Load Tridnet Mapping")
        with open(trident_mapping_file) as f:
            mapping_dict = json.load(f)

        login = []
        login = config_dict["login"]["initiator"]["client"]
        login.append(config_dict["login"]["target"]["server"][0])

        pos = POS("pos_config.json")
        if trident_config_data["dump_pos_core"]["enable"] == "true":
            pos.set_collect_core(get_core_dump=True)
            logger.info("POS core dump collection enabled")

        logger.info("Trident Init Sequence Completed !!!")
    except Exception as e:
        logger.error(f"Trident Init Sequence Failed due to {e}")
        return False
    return True


def pos_cce_init():
    try:
        if trident_config_data["code_coverage"]["enable"] == "true":
            logger.debug("Init POS code coverage extraction...")
            global cc
            cce_config_file = trident_config_data["code_coverage"]["config_file"]
            cc = CodeCoverage(cce_config_file)
            assert cc.target_init() == True
            assert cc.databse_init() == True
        else:
            logger.debug("POS code coverage extraction is not enable")
    except Exception as e:
        logger.error(f"Failed to Init code coverage extraction due to {e}")
        return False
    return True

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

 ######################################  Pytest Functions #####################

def pytest_sessionstart(session):
    """ Pytest Session Start """
    global session_start_time
    session_start_time = datetime.now()
    start_time = session_start_time.strftime("%m/%d/%Y, %H:%M:%S")
    logger.info(f"Test Session Start Time : {start_time}")
    
    assert trident_test_init() == True
    assert pos_cce_init() == True

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

def teardown_session():
    logger.info("============= CLEANUP SESSION AFER TEST")
    pos.exit_handler(expected=False)

 ###################################### Pytest Fixtures ######################

@pytest.fixture(scope="function")
def system_fixture():
    logger.info("========== SETUP BEFORE TEST =========")

    # Stop POS if running before test
    if pos.target_utils.helper.check_pos_exit() == False:
        assert pos.cli.pos_stop(grace_shutdown = False) == True

    yield pos

    # Stop POS if running after test
    if pos.target_utils.helper.check_pos_exit() == False:
        assert pos.cli.pos_stop(grace_shutdown = False) == True
        

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

 ###################################### Functions ############################

def check_pos_and_bringup():
    try:
        pos.data_dict["system"]["phase"] = "true"
        pos.data_dict["subsystem"]["phase"] = "true"
        pos.data_dict["device"]["phase"] = "true"
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.bringup_system(data_dict=pos.data_dict) == True
            assert pos.target_utils.bringup_device(data_dict=pos.data_dict) == True
            assert pos.target_utils.bringup_subsystem(data_dict=pos.data_dict) == True
            assert pos.target_utils.get_subsystems_list() == True
            array_cleanup()
        else:
            logger.info("pos is already running")
            assert pos.cli.device_scan()[0] == True
            array_cleanup()
            
        return True
    except Exception as e:
        logger.error(e)
        traceback.print_exc()
        assert pos.cli.pos_stop(grace_shutdown=False)[0] == True
        return False

def client_teardown(is_pos_running: bool) -> bool:
    """ Teardown function reset client """
    pos.client.reset(pos_run_status=is_pos_running) 
    return True

def target_teardown(is_pos_running: bool): 
    """ Teardown function to reset target """
    assert pos.target_utils.helper.check_system_memory() == True
    if is_pos_running:
        try:
            array_cleanup()
        except Exception as e:
            logger.error(f"Array cleanup failed due to {e}")
            # Stop POS as array cleanup failed
            assert pos.cli.pos_stop(grace_shutdown=False)[0] == True
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

def pos_logs_core_dump(report, issuekey):
    time_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_key = f"{issuekey}_{time_stamp}"
    if (report.when == 'call' and report.outcome == 'failed'):
        #TODO update pos path

        if trident_config_data["dump_pos_core"]["enable"] == "true":
            assert pos.target_utils.copy_core(unique_key) == True

        if trident_config_data["copy_pos_log"]["test_fail"] == "true":
            assert pos.target_utils.copy_pos_log(unique_key) == True

    elif (report.when == 'call' and report.outcome == 'passed' and
        trident_config_data["copy_pos_log"]["test_pass"] == "true"):
            assert pos.target_utils.copy_pos_log(unique_key) == True
    return True

 ###################################### ELK Tags #############################

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
