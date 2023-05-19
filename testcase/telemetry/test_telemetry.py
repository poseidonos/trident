import pytest
import logger
logger = logger.get_logger(__name__)

@pytest.mark.sanity
def test_telemetry(system_fixture):
    try:
        pos = system_fixture
        if pos.pos_as_service == False: 
            pytest.skip("POS should run as a service for telemetry to work")

        assert pos.target_utils.pos_bring_up() == True
        assert pos.prometheus.update_config() == True
        assert pos.prometheus.set_telemetry_configs() == True
        assert pos.prometheus.get_all_metrics() == True
    except Exception as e:
        logger.error(e)
        assert 0
