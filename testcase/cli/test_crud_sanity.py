import pytest

import re
import time
from common_libs import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.sanity
def test_crud_array_ops_all_raids(array_fixture):
    """
    The purpose of this test is to do array crud operation with following matrix.

    RAID Types - (no-raid, raid0, raid5, raid6, raid10)
    Operations - 
        C: create / autocreate
        R: list
        U: addspare / mount / rebuild / replace / rmspare / unmount
        D: delete

    Verification: POS CLI - Array CRUD Operation.
    """
    logger.info(
        f" ==================== Test : test_crud_array_ops_all_raids ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        
        for arr1_raid in ARRAY_ALL_RAID_LIST:
            arr2_raid = random.choice(ARRAY_ALL_RAID_LIST)
            arr1_disk = RAID_MIN_DISK_REQ_DICT[arr1_raid]
            arr2_disk = RAID_MIN_DISK_REQ_DICT[arr2_raid]

            if (arr1_disk + arr2_disk + 2) > len(system_disks):
                logger.warning("Array creation requied more disk")
                continue

            assert multi_array_data_setup(pos.data_dict, 2, (arr1_raid, arr2_raid),
                                          (arr1_disk, arr2_disk), (0, 0), 
                                          ("WT", "WT"), (False, True)) == True

            # Create, Read and Update Ops
            assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

            # Read and Update Ops
            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())

            assert pos.cli.device_list()[0] == True
            system_disks = pos.cli.system_disks
            for array_name in array_list:
                assert pos.cli.array_info(array_name=array_name)[0] == True
                array_raid = pos.cli.array_data[array_name]["data_raid"]
                data_disk = pos.cli.array_data[array_name]["data_list"]

                # spare disk is not supported, continue
                logger.info(f"Array Raid {array_raid}")
                if array_raid == "RAID0" or array_raid == 'NONE':
                    continue

                spare_disk = system_disks.pop(0)
                assert pos.cli.array_addspare(device_name=spare_disk,
                                              array_name=array_name)[0] == True
                
                assert pos.cli.array_rmspare(device_name=spare_disk,
                                             array_name=array_name)[0] == True
                
                assert pos.cli.array_addspare(device_name=spare_disk,
                                              array_name=array_name)[0] == True

                assert pos.cli.array_replace_disk(device_name=data_disk[0],
                                                array_name=array_name)[0] == True
                assert pos.target_utils.array_rebuild_wait(array_name=array_name) == True

                # 30 sec sleep after rebuild
                time.sleep(30)

            # Update and Delete Operation
            assert array_unmount_and_delete(pos) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.sanity
def test_crud_listner_ops(system_fixture):
    """
    The purpose of this test is to do listner crud operation with following matrix.

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
        for subsystem in pos.target_utils.ss_temp_list:
            # Read - List Listner (No Listener)
            assert pos.cli.subsystem_list_listener(subsystem)[0] == True
            assert len(pos.cli.subsystem_listeners[subsystem]) == 0

            # Update - Add Listner
            assert pos.cli.subsystem_add_listner(subsystem,
                                        ip_addr, "1158")[0] == True

            # Read - List Listner
            assert pos.cli.subsystem_list_listener(subsystem)[0] == True
            assert len(pos.cli.subsystem_listeners[subsystem]) == 1

            # Update - Remove Listner
            assert pos.cli.subsystem_remove_listener(subsystem,
                                        ip_addr, "1158")[0] == True 

            # Read - List Listner
            assert pos.cli.subsystem_list_listener(subsystem)[0] == True
            assert len(pos.cli.subsystem_listeners[subsystem]) == 0                      

        # Delete Subsystem
        for subsystem in pos.target_utils.ss_temp_list:
            assert pos.cli.subsystem_delete(subsystem)[0] == True

        # Read - Subsystem List
        assert pos.target_utils.get_subsystems_list() == True
        assert len(pos.target_utils.ss_temp_list) == 0

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.sanity
def test_crud_subsystem_ops(system_fixture):
    """
    The purpose of this test is to do subsystem crud operation with following matrix.

    Operations - 
        C: create / create-transport
        R: list
        U: add-listener
        D: delete

    Verification: POS CLI - Array CRUD Operation.
    """
    logger.info("================ test_npor_with_half_uram ================")
    try:
        pos = system_fixture
        data_dict = pos.data_dict

        assert pos.cli.pos_start()[0] == True

        # Create - Create Transport
        assert pos.cli.subsystem_create_transport(buf_cache_size=64,
                    num_shared_buf=4096, transport_type="TCP")[0] == True
        
        # Create - Create 1024 susbsystem 
        for ss_nr in range(1, 1024):
            nqn = f"nqn.2022-10.pos-array:subsystem{ss_nr}"
            ns_count = 512
            serial_number = "POS000000%04d"%ss_nr
            model_number = "POS_VOLUME_array"

            assert pos.cli.subsystem_create(nqn, ns_count, serial_number,
                                            model_number)[0] == True
            logger.info(f"Subsystem {ss_nr} created successfully.")
            
        # Read - Subsystem List 1023 + 1 discovery
        assert pos.target_utils.get_subsystems_list() == True
        assert len(pos.target_utils.ss_temp_list) == 1023

        # Update - Add Listner
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for subsystem in pos.target_utils.ss_temp_list:
            assert pos.cli.subsystem_add_listner(subsystem,
                                        ip_addr, "1158")[0] == True
            
        # Connect to all subsystems from initiator
        for nqn in pos.target_utils.ss_temp_list[:256]:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        # Disconnect half subsystems from initiator
        for nqn in pos.target_utils.ss_temp_list[:128]:
            assert pos.client.nvme_disconnect(nqn, ip_addr, "1158") == True

        # Delete Subsystem
        for subsystem in pos.target_utils.ss_temp_list:
            assert pos.cli.subsystem_delete(subsystem)[0] == True

        # Disconnect half subsystems from initiator
        for nqn in pos.target_utils.ss_temp_list[128:256]:
            assert pos.client.nvme_disconnect(nqn, ip_addr, "1158") == True

        # Read - Subsystem List
        assert pos.target_utils.get_subsystems_list() == True
        assert len(pos.target_utils.ss_temp_list) == 0

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.sanity
def test_crud_transport_ops(system_fixture):
    """
    The purpose of this test is to do transport crud operation with following matrix.

    Operations - 
        C: create
        R: list

    Verification: POS CLI - Transport CRUD Operation.
    """
    logger.info("================ test_crud_transport_ops ================")
    try:
        pos = system_fixture
        data_dict = pos.data_dict

        assert pos.cli.pos_start()[0] == True

        # Create - Create Transport
        assert pos.cli.transport_create(buf_cache_size=64,
                    num_shared_buf=4096, transport_type="TCP")[0] == True

        # Read - List Transport
        assert pos.cli.transport_list()[0] == True

        logger.info(f"Num of Transport : {pos.cli.num_transport}")
        assert pos.cli.num_transport == 1

        for transport in pos.cli.transports:
            logger.info(f"tr_type : {transport['tr_type']}, " 
                        f"q_depth: {transport['q_depth']}")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.sanity
def test_crud_volume_ops(array_fixture):
    """
    The purpose of this test is to do volume crud operation on RAID5 and RAID10
    arrays for following matrix.

    Array RAID Types - (raid5, raid10)
    Operations - 
        C: create
        R: list
        U: mount / mount-with-subsystem / rename / set-property / unmount
        D: delete

    Verification: POS CLI - Volume CRUD Operation.
    """
    logger.info(
        f" ==================== Test : test_crud_volume_ops ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        
        arr1_raid, arr2_raid = "RAID5", "RAID10"

        arr1_disk = RAID_MIN_DISK_REQ_DICT[arr1_raid]
        arr2_disk = RAID_MIN_DISK_REQ_DICT[arr2_raid]

        if (arr1_disk + arr2_disk + 2) > len(system_disks):
            pytest.skip("Array creation requied more disk")

        assert multi_array_data_setup(pos.data_dict, 2, (arr1_raid, arr2_raid),
                                        (arr1_disk, arr2_disk), (0, 0), 
                                        ("WT", "WT"), (False, True)) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        array_list = list(pos.cli.array_dict.keys())

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list

        nr_vol_list = [1, 16, 256]
        for num_vols in nr_vol_list:
            logger.info(f"Create, Mount, List, Unmount, Delete {num_vols} Vols")
            # Create, Read and Update Ops
            assert volume_create_and_mount_multiple(pos, num_vols, 
                        array_list=array_list, subs_list=subs_list) == True
            
            # Update and Delete Operation
            assert volume_unmount_and_delete_multiple(pos, array_list) == True

        # Create 2 volumes from each array
        assert volume_create_and_mount_multiple(pos, 2, array_list=array_list,
                                mount_vols=False, subs_list=subs_list) == True
        
        for array_name in array_list:
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name in pos.cli.vol_dict.keys():
                assert pos.cli.volume_rename("new" + vol_name, vol_name,
                                        array_name=array_name)[0] == True
                #assert pos.cli.volume_mount_with_subsystem()

        # Update and Delete Operation
        assert volume_unmount_and_delete_multiple(pos, array_list) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
