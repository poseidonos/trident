import pytest
import logger
logger = logger.get_logger(__name__)
from pos import POS
@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos
    pos = POS()
    if pos.pos_as_service == False: 
        pytest.skip("POS should run as a service for telemetry to work")

    assert pos.target_utils.pos_bring_up() == True
    
    assert pos.prometheus.update_config() == True
    assert pos.prometheus.set_telemetry_configs() == True
    yield pos

def teardown_function():

    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.array_list()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.array_info(array_name=array)[0] == True
            # assert pos.cli.wbt_flush(array_name=array)[0] == True ## for code coverage
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.array_unmount(array_name=array)[0] == True

    assert pos.cli.devel_resetmbr()[0] == True
    assert pos.target_utils.pci_rescan() == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

@pytest.mark.sanity
def test_telemetry():
    try:
         assert pos.prometheus.get_all_metrics() == True
    except Exception as e:
        logger.error(e)
        assert 0
