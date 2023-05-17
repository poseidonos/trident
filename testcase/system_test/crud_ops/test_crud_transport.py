import pytest
import logger

logger = logger.get_logger(__name__)

def test_crud_transport_negative(system_fixture):
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

        # Create - Re Create Transport
        assert pos.cli.transport_create(buf_cache_size=64,
                    num_shared_buf=4096, transport_type="TCP")[0] == False

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

