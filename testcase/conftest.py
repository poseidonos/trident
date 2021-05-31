import pytest, traceback, sys, json, os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))
import logger as logging

logger = logging.get_logger(__name__)

from utils import Client as client
from client_conf import Hostconf as nvme_manager
from node import SSHclient as node
from target_conf import PoSos
from pos import POS

dir_path = os.path.dirname(os.path.realpath(__file__))
with open("{}/config_files/topology.json".format(dir_path)) as f:
    config_dict = json.load(f)


def pytest_sessionstart(session):
    global session_start_time
    session_start_time = datetime.now()
    logger.info("Test Session Start Time : {}".format(session_start_time.strftime("%m/%d/%Y, %H:%M:%S")))

@pytest.hookimpl(tryfirst=False, hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    driver = item.nodeid.split("::")[0]
    method = item.nodeid.split("::")[1]
    logger.info("======================== START OF {} ========================".format(method))
    start_time = datetime.now()
    logger.info("Start Time : {}".format(start_time.strftime("%m/%d/%Y, %H:%M:%S")))
    yield
    end_time = datetime.now()
    logger.info("End Time : {}".format(end_time.strftime("%m/%d/%Y, %H:%M:%S")))
    execution_time = end_time-start_time
    execution_minutes = divmod(execution_time.seconds, 60)
    logger.info("Execution Time : {} minutes {} seconds".format(execution_minutes[0], execution_minutes[1]))
    logger.info("======================== END OF {} ========================".format(method))

def pytest_runtest_logreport(report):
    if report.when == "setup":
        setup_status = report.outcome
        if setup_status == "failed":
            logger.info("======================== Test Status : {} ========================".format("FAIL"))
        elif setup_status == "skipped":
            logger.info("======================== Test Status : {} ========================".format("SKIP"))
    if report.when == "call":
        test_status = report.outcome
        if test_status == "passed":
            logger.info("======================== Test Status : {} ========================".format("PASS"))
        elif test_status == "failed":
            logger.info("======================== Test Status : {} ========================".format("FAIL"))

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    log_path = logging.get_logpath()
    config.option.htmlpath = log_path + "/report.html"
    config.option.self_contained_html = True

def pytest_sessionfinish(session):
    session_end_time = datetime.now()
    log_path = logging.get_logpath()
    logger.info("Test Session End Time : {}".format(session_end_time.strftime("%m/%d/%Y, %H:%M:%S")))
    session_time = session_end_time - session_start_time
    session_minutes = divmod(session_time.seconds, 60)
    logger.info("Total Session Time : {} minutes {} seconds".format(session_minutes[0], session_minutes[1]))
    logger.info("Logs and Html report for executed TCs are present in {}".format(log_path))

@pytest.fixture(scope = "module")

def array_fixture():

    '''Steps to setup target and pos instance'''
    ip_addr = config_dict['login']['target'][0]
    user_name = config_dict['login']['target'][1]
    passwd = config_dict['login']['target'][2]
    pos_path = config_dict['login']['paths']['pos_path']

    target_obj = node(ip_addr, user_name, passwd)
    pos_obj = POS(target_obj, pos_path)
    target_setup = PoSos(pos_obj)
    '''setup envirenment  for pos'''
    target_setup.setup_env_pos()
    if target_setup.status['ret_code'] is "fail":
       logger.error(target_setup.status['message'])
       pytest.skip()
    else:
       logger.info(target_setup.status['message'])

    '''start  pos os should successfully start the pos os'''
    target_setup.start_pos_os()
    if target_setup.status['ret_code'] is "fail":
       logger.error(target_setup.status['message'])
       pytest.skip()
    else:
       logger.info(target_setup.status['message'])

    '''create malloc_device should successfully create RAM device'''
    target_setup.create_malloc_device()
    if target_setup.status['ret_code'] is "fail":
       logger.error(target_setup.status['message'])
       pytest.skip()
    else:
       logger.info(target_setup.status['message'])

    '''scan_device should successfully scan the device'''
    target_setup.scan_devs()
    if target_setup.status['ret_code'] is "fail":
       logger.error(target_setup.status['message'])
       pytest.skip()
    else:
       logger.info(target_setup.status['message'])

    ''' creating nvmf subsystem'''
    target_setup.create_Nvmf_SS()
    if target_setup.status['ret_code'] is "fail":
       logger.error(target_setup.status['message'])
       pytest.skip()
    else:
       logger.info(target_setup.status['message'])

    ''' list device should successfully list the devices'''
    target_setup.list_devs()
    if target_setup.status['ret_code'] is "fail":
       logger.error(target_setup.status['message'])
       pytest.skip()
    else:
       logger.info(target_setup.status['message'])

    yield target_setup
    target_setup.stop()
    target_obj.close()

@pytest.fixture(scope = "module")

def vol_fixture(array_fixture):

    '''create array'''
    array_fixture.create_array(array_name = "POSARRAY1")
    if array_fixture.status['ret_code'] is "fail":
       logger.error(array_fixture.status['message'])
       pytest.skip()
    else:
       logger.info(array_fixture.status['message'])

    '''Mounting array'''
    array_fixture.mount_array(array_name = "POSARRAY1")
    if array_fixture.status['ret_code'] is "fail":
       logger.error(array_fixture.status['message'])
       pytest.skip()
    else:
       logger.info(array_fixture.status['message'])

    yield array_fixture

@pytest.fixture(scope = "module")

def user_io(vol_fixture):
    connect_flag = False
    client_ip = config_dict['login']['initiator'][0]
    client_user = config_dict['login']['initiator'][1]
    client_passwd = config_dict['login']['initiator'][2]

    '''Steps to setup client'''
    client_obj = node(client_ip, client_user, client_passwd)
    utils_obj = client(client_obj)
    client_setup = nvme_manager(utils_obj)

    ''' creating and mounting multiple volume '''
    vol_fixture.create_mount_multiple(num_vols = 5, size = "100gb",array_name = "POSARRAY1")
    if vol_fixture.status['ret_code'] is "fail":
       logger.error(vol_fixture.status['message'])
       pytest.skip()
    else:
       logger.info(vol_fixture.status['message'])

    ''' create nvmf transport '''
    vol_fixture.create_transport()
    if vol_fixture.status['ret_code'] is "fail":
       logger.error(vol_fixture.status['message'])
       pytest.skip()
    else:
       logger.info(vol_fixture.status['message'])

    ''' add nvmf listner  '''
    vol_fixture.add_nvmf_listner(mellanox_interface = config_dict['login']['tar_mlnx_ip'])
    if vol_fixture.status['ret_code'] is "fail":
       logger.error(vol_fixture.status['message'])
       pytest.skip()
    else:
       logger.info(vol_fixture.status['message'])

    ''' connect nqn to initiator  '''
    client_setup.nvme_connect(vol_fixture.nqn_name, config_dict['login']['tar_mlnx_ip'])
    if client_setup.status['ret_code'] is "fail":
       logger.error(client_setup.status['message'])
       pytest.skip()
    else:
       connect_flag = True 
       logger.info("Nvme subsystem {} connected to host machine {}".format(vol_fixture.nqn_name, config_dict['login']['initiator'][0]))

    '''listing nvme devices '''
    client_setup.list_nvme()
    if client_setup.status['ret_code'] is "fail":
       logger.error(client_setup.status['message'])
       pytest.skip()
    else:
       connect_flag = True 
       logger.info(client_setup.status['message'])
    objs = {"target_setup":vol_fixture,"client_setup":client_setup}
    yield objs
    if connect_flag:
       client_setup.nvme_disconnect()
