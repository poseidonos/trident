import time
import pytest
from common_libs import *
import logger

logger = logger.get_logger(__name__)
metric = ['criticalTemperatureTime', 'lifePercentageUsed', 'availableSpare', 'availableSpareThreshold',
          'currentTemperature', 'powerCycles', 'powerOnHours', 'controllerBusyTime', 'unsafeShutdowns',
          'warningTemperatureTime', 'unrecoverableMediaErrors']


@pytest.mark.parametrize("metric", metric)
def test_get_smart_stats(array_fixture, metric):
    pos = array_fixture
    assert pos.cli.pos_xpo_service_start()[0] == True
    assert pos.prometheus.set_telemetry_configs() == True
    assert pos.cli.device_scan()[0] == True
    assert pos.cli.device_list()
    disk = pos.cli.system_disks[0]
    assert pos.cli.device_smart_log(devicename=disk)[0] == True
    logger.info(pos.cli.smart_log_dict[disk])
    if metric == 'criticalTemperatureTime':
        time.sleep(60)
    logger.info(pos.prometheus.get_uptime_sec())
    assert pos.prometheus.get_smart_stats(device_name=disk) == True
    logger.info(pos.prometheus.result)
    assert pos.prometheus.result[metric] in pos.cli.smart_log_dict[disk][metric]
