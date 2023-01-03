import time
from common_libs import *
import logger
import os
logger = logger.get_logger(__name__)

def test_get_smart_stats(array_fixture):
    pos = array_fixture
    assert pos.cli.pos_exporter(operation='start')[0] == True
    assert pos.prometheus.set_telemetry_configs() == True
    assert pos.cli.scan_device()[0] == True
    disk = pos.cli.system_disks[0]
    assert pos.cli.smart_log_device(devicename=disk)[0] == True
    time.sleep(60)
    assert pos.prometheus.get_smart_stats(device_name=disk) == True
    logger.info(pos.prometheus.result)