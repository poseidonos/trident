import pytest
import logger

logger = logger.get_logger(__name__)

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

