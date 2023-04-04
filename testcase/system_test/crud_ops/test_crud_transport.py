import pytest
import logger

logger = logger.get_logger(__name__)

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

        logger.info("Num of Transport : {pos.cli.num_transport}")
        assert pos.cli.num_transport == 1

        for transport in pos.cli.transport_list:
            logger.info(f"tr_type : {transport['tr_type']}, " 
                        f"q_depth: {transport['q_depth']}")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

