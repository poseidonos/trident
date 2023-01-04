import time
from common_libs import *
import logger
import os
logger = logger.get_logger(__name__)

def test_volume_io_metrics(array_fixture):
    pos = array_fixture
    arrays =  array_and_volume_creation(pos=pos,run_io=False)
    nvme_devs = nvme_connect(pos=pos)[1]
    fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randrw --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=20 --verify=md5"
    out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                  fio_user_data=fio_cmd, run_async=True)
    assert out == True
    assert pos.prometheus.get_all_metrics() == True
    logger.info(pos.prometheus.promlist)
    assert pos.prometheus.publish_io_metrics() == True
    logger.info(pos.prometheus.metric_data)
    assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True
