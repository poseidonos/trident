import pytest
import re
from time import sleep
from common_libs import *

import logger
logger = logger.get_logger(__name__)

def test_crud_listner_negative_ops(system_fixture):
    """
    The purpose of this test is to do listner crud operation with getavie values.

    Operations - 
        C: create / create-transport
        R: list-listner
        U: add-listener
        D: remove-listener

    Verification: POS CLI - Subsystem Listner CRUD Operation.
    """
    logger.info("================ test_crud_listner_ops ================")
    try:
        pos = system_fixture
        data_dict = pos.data_dict

        assert pos.cli.pos_start()[0] == True

        # Create - Create Transport
        assert pos.cli.subsystem_create_transport(buf_cache_size=64,
                    num_shared_buf=4096, transport_type="TCP")[0] == True
        
        # Create - Create 1 susbsystem 
        nqn = f"nqn.2022-10.pos-array:subsystem1"
        assert pos.cli.subsystem_create(nqn)[0] == True
            
        # Read - Subsystem List 
        assert pos.target_utils.get_subsystems_list() == True
        assert nqn == pos.target_utils.ss_temp_list[0]

        ip_addr = pos.target_utils.helper.ip_addr[0]
        subsystem = pos.target_utils.ss_temp_list.pop(0)

        ip_invalid = "127.0.255.256"
        ss_invalid = subsystem + "_invalid"
        port_invalid = "-1"
        exp = lambda exp: "{}".format(int(exp.groups()[0]) + 1)
        ip_wrong = re.sub(r"(\d{1,3})$", exp, ip_addr)

        # Test 1 - Add Listner with invalid IP 1
        assert pos.cli.subsystem_add_listner(subsystem,
                            ip_invalid, "1158")[0] == False
        logger.info(f"Expected failure for add listener with invalid IP {ip_invalid}")

        # Test 2 - Add Listner with wrong IP 

        assert pos.cli.subsystem_add_listner(subsystem,
                            ip_wrong, "1158")[0] == False
        logger.info(f"Expected failure for add listener with invalid IP {ip_wrong}")

        # Test 3 - Add Listner with invalid port
        assert pos.cli.subsystem_add_listner(subsystem,
                            ip_addr, port_invalid)[0] == False
        logger.info(f"Expected failure for add listener with invalid PORT")

        # Test 4 - Add Listner with invalid subsystem name
        assert pos.cli.subsystem_add_listner(ss_invalid,
                            ip_addr, "1158")[0] == False
        logger.info(f"Expected failure for add listener with invalid nqn")

        # Test 5 - Remove Listner which is not added
        assert pos.cli.subsystem_remove_listener(subsystem,
                                    ip_addr, "1158")[0] == False
        logger.info(f"Expected failure for remove listener before add")

        # Add Listner
        assert pos.cli.subsystem_add_listner(subsystem,
                                    ip_addr, "1158")[0] == True

        # Test 6 - List Listner with invalid subsystem name
        assert pos.cli.subsystem_list_listener(ss_invalid)[0] == False
        logger.info(f"Expected failure for list listener with invalid nqn")

        # Test 7 - Remove Listner with invalid IP name
        assert pos.cli.subsystem_remove_listener(subsystem,
                                    ip_invalid, "1158")[0] == False
        logger.info(f"Expected failure for remove listener with invalid IP")

        # Test 8 - Remove Listner with invalid Port name
        assert pos.cli.subsystem_remove_listener(subsystem,
                                    ip_addr, "1200")[0] == False
        logger.info(f"Expected failure for remove listener with invalid port")                 

        # Delete Subsystem
        assert pos.cli.subsystem_delete(subsystem)[0] == True

        # Test 9 - Remove Listner from deleted sybsystem
        assert pos.cli.subsystem_remove_listener(subsystem,
                                    ip_addr, "1158")[0] == False
        logger.info(f"Expected failure for remove listener for no subsys")

        # Read - Subsystem List
        assert pos.target_utils.get_subsystems_list() == True
        assert len(pos.target_utils.ss_temp_list) == 0

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_listner_remove_during_io(volume_fixture):
    """
    The purpose of this test is to do listner remove during IO.

    Operations - 
        R: list-listner
        U: add-listener
        D: remove-listener

    Verification: POS CLI - Subsystem Listner CRUD Operation and system behaviour during.
    """
    logger.info("================ test_listner_remove_during_io ================")
    try:
        pos = volume_fixture
        data_dict = pos.data_dict

        # Read - Subsystem List 
        assert pos.target_utils.get_subsystems_list() == True

        volume_create_and_mount_multiple(pos, num_volumes=2, vol_size="10GB",
                            subs_list=pos.target_utils.ss_temp_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]

        for nqn in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        logger.info(f"******** Start IO *****************")

        fio_cmd = "fio --name=test_randwrite --ioengine=libaio --rw=randwrite "
        fio_cmd += "--iodepth=64 --bs=128k --time_based=1 --runtime=300" 

        out, async_io = pos.client.fio_generic_runner(nvme_devs,
                            fio_user_data=fio_cmd, run_async=True)
        assert out == True

        sleep(120)

        subsystem = pos.target_utils.ss_temp_list[0]
        # Read - List Listner
        assert pos.cli.subsystem_list_listener(subsystem)[0] == True

        listener_addr = pos.cli.subsystem_listeners[subsystem][0]["address"]
        ip_addr = listener_addr['traddr']
        ip_port = listener_addr['trsvcid']
        tr_type = listener_addr['trtype']

        # Update - Remove Listner
        assert pos.cli.subsystem_remove_listener(subsystem,
                        ip_addr, ip_port, tr_type)[0] == True 

        # Update - Add Listner
        assert pos.cli.subsystem_add_listner(subsystem,
                        ip_addr, ip_port, tr_type)[0] == True

        # Wait for async fio to complete
        assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=30) == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

