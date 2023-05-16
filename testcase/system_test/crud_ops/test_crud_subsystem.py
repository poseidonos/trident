import pytest
import logger

logger = logger.get_logger(__name__)

def test_crud_subsystem_negative_ops(system_fixture):
    """
    The purpose of this test is to do subsystem negative crud operations.

    Operations - 
        C: create / create-transport
        R: list
        U: add-listener
        D: delete

    Verification: POS CLI - Array CRUD Operation.
    """
    logger.info("================ test_crud_subsystem_negative_ops ================")
    try:
        pos = system_fixture
        data_dict = pos.data_dict

        assert pos.cli.pos_start()[0] == True

        # Create - Create Transport Invalid Type
        assert pos.cli.subsystem_create_transport(buf_cache_size=64,
                    num_shared_buf=4096, transport_type="INVALID")[0] == False
        logger.info(f"Expected failure for transport create with invalid type")
        
        # Create - Create susbsystem with invalid nqn
        nqn = f"nqn.2022-10.pos-subsystem_{'ab_' * 10}"
        serial = "POS000000%04d"%1
        assert pos.cli.subsystem_create(nqn, serial_number=serial)[0] == False
        logger.info(f"Expected failure for subsystem create with invalid nqn")

        # Update - Add Listner to invalid nqn
        ip_addr = pos.target_utils.helper.ip_addr[0]
        assert pos.cli.subsystem_add_listner(nqn, ip_addr, "1158")[0] == False
        logger.info(f"Expected failure for add listner to invalid subsystem")
            
        # Connect to invalid subsystems from initiator
        assert pos.client.nvme_connect(nqn, ip_addr, "1158") == False
        logger.info(f"Expected failure for nvme connect with invalid nqn")
    except Exception as e:
        logger.error(f"Test Script failed due to {e}")
        pos.exit_handler(expected=False)
