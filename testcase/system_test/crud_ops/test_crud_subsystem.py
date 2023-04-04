import pytest
import logger

logger = logger.get_logger(__name__)

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
