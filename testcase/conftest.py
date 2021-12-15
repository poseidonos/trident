#/*
# *   BSD LICENSE
# *   Copyright (c) 2021 Samsung Electronics Corporation
# *   All rights reserved.
# *
# *   Redistribution and use in source and binary forms, with or without
# *   modification, are permitted provided that the following conditions
# *   are met:
# *
# *     * Redistributions of source code must retain the above copyright
# *       notice, this list of conditions and the following disclaimer.
# *     * Redistributions in binary form must reproduce the above copyright
# *       notice, this list of conditions and the following disclaimer in
# *       the documentation and/or other materials provided with the
# *       distribution.
# *     * Neither the name of Samsung Electronics Corporation nor the names of
# *       its contributors may be used to endorse or promote products derived
# *       from this software without specific prior written permission.
# *
# *   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# *   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# *   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# *   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# *   OWN
#/*
import pytest, sys, json, os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
import logger as logging

logger = logging.get_logger(__name__)
from pos import POS
from utils import Client

dir_path = os.path.dirname(os.path.realpath(__file__))
with open("{}/config_files/topology.json".format(dir_path)) as f:
    config_dict = json.load(f)
    logger.info(config_dict)


def pytest_sessionstart(session):
    global session_start_time
    session_start_time = datetime.now()
    logger.info(
        "Test Session Start Time : {}".format(
            session_start_time.strftime("%m/%d/%Y, %H:%M:%S")
        )
    )


@pytest.hookimpl(tryfirst=False, hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    driver = item.nodeid.split("::")[0]
    method = item.nodeid.split("::")[1]
    logger.info(
        "======================== START OF {} ========================".format(method)
    )
    start_time = datetime.now()
    logger.info("Start Time : {}".format(start_time.strftime("%m/%d/%Y, %H:%M:%S")))
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
    logger.info(
        "======================== END OF {} ========================".format(method)
    )


def pytest_runtest_logreport(report):
    if report.when == "setup":
        setup_status = report.outcome
        if setup_status == "failed":
            logger.info(
                "======================== Test Status : {} ========================".format(
                    "FAIL"
                )
            )
        elif setup_status == "skipped":
            logger.info(
                "======================== Test Status : {} ========================".format(
                    "SKIP"
                )
            )
    if report.when == "call":
        test_status = report.outcome
        if test_status == "passed":
            logger.info(
                "======================== Test Status : {} ========================".format(
                    "PASS"
                )
            )
        elif test_status == "failed":
            logger.info(
                "======================== Test Status : {} ========================".format(
                    "FAIL"
                )
            )


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


target_obj, pos, client_obj, client_setup = None, None, None, None


def init_client():
    global client_obj, client_setup
    client_obj = Client(
        config_dict["login"]["initiator"]["ip"],
        config_dict["login"]["initiator"]["username"],
        config_dict["login"]["initiator"]["password"],
    )
    return client_obj


@pytest.fixture(scope="module")
def start_pos():
    try:
        global pos
        pos = POS(
            config_dict["login"]["target"]["ip"],
            config_dict["login"]["target"]["username"],
            config_dict["login"]["target"]["password"],
            config_dict["login"]["paths"]["pos_path"],
        )
        assert pos.cli.start_system()[0] == True
    except Exception as e:
        logger.error(e)
        assert 0
    yield pos
    pos.cli.stop_system(grace_shutdown=False)


@pytest.fixture(scope="module")
def scan_dev(start_pos):
    try:
        global nqn_name
        assert pos.cli.create_device()[0] == True
        assert pos.cli.scan_device()[0] == True
        nqn_name = pos.target_utils.generate_nqn_name()
        assert pos.cli.create_subsystem(nqn_name)[0] == True

    except Exception as e:
        logger.error(e)
        assert 0
    yield start_pos


@pytest.fixture(scope="module")
def array_management(scan_dev):
    try:
        assert pos.cli.reset_devel()[0] == True
        assert pos.cli.create_array()[0] == True
    except Exception as e:
        logger.error(e)
        assert 0
    yield scan_dev


@pytest.fixture(scope="module")
def mount_array(array_management):
    try:
        assert pos.cli.mount_array()[0] == True
    except Exception as e:
        logger.error(e)
        assert 0
    yield array_management


@pytest.fixture(scope="module")
def vol_fixture(mount_array):
    try:
        assert pos.target_utils.create_mount_multiple() == True
    except Exception as e:
        logger.error(e)
        assert 0
    yield mount_array


@pytest.fixture(scope="module")
def nvmf_transport(vol_fixture):
    try:
        pos.cli.create_transport_subsystem()[0]
        pos.cli.add_listner_subsystem(
            nqn_name, config_dict["login"]["tar_mlnx_ip"], "1158"
        )[0]
    except Exception as e:
        logger.error(e)
        assert 0
    yield vol_fixture


@pytest.fixture(scope="function")
def user_io(nvmf_transport):
    client = init_client()
    client.nvme_connect(nqn_name, config_dict["login"]["tar_mlnx_ip"], "1158")
    combo = {"client": client, "target": pos}
    yield combo
    client.nvme_disconnect()
