import time
from common_libs import *
import logger
import os
logger = logger.get_logger(__name__)


def array_and_volume_creation(pos,num_array=1,num_vol=1,run_io=True):
    # Bring up arrays and volumes and run io
    pos.data_dict["array"]["num_array"] = num_array
    assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
    assert pos.cli.array_list()[0] == True
    arrays = list(pos.cli.array_dict.keys())
    assert pos.target_utils.get_subsystems_list() == True
    assert volume_create_and_mount_multiple(pos=pos, num_volumes=num_vol, array_list=[arrays[0]],
                                            subs_list=pos.target_utils.ss_temp_list) == True
    if run_io == True:
        assert vol_connect_and_run_random_io(pos, pos.target_utils.ss_temp_list, size='1g') == True
    return arrays


io_metrics = ["read_iops_device","read_bps_device","write_bps_device","write_iops_device",
              "read_iops_network","read_bps_network","write_iops_network","write_bps_network"
              "read_iops_volume","read_bps_volume","write_iops_volume","write_bps_volume",
              "read_avg_lat_volume","write_avg_lat_volume"]
@pytest.mark.parametrize("metric",io_metrics)
def test_io_metric(array_fixture,metric):
    pos = array_fixture
    arrays =  array_and_volume_creation(pos=pos,run_io=False)
    nvme_devs = nvme_connect(pos=pos)[1]
    fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randrw --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=100 --verify=md5"
    out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                  fio_user_data=fio_cmd, run_async=True)
    assert out == True
    if metric == "read_iops_device":
        assert pos.prometheus.get_read_iops_device() == True
    elif metric == "read_bps_device":
        assert pos.prometheus.get_read_bps_device() == True
    elif metric == "write_bps_device":
        assert pos.prometheus.get_write_bps_device() == True
    elif metric == "write_iops_device":
        assert pos.prometheus.get_write_iops_device() == True
    elif metric == "read_iops_network":
        assert pos.prometheus.get_read_iops_network() == True
    elif metric == "read_bps_network":
        assert pos.prometheus.get_read_bps_network() == True
    elif metric == "write_iops_network":
        assert pos.prometheus.get_write_iops_network() == True
    elif metric == "write_bps_network":
        assert pos.prometheus.get_write_bps_network() == True
    elif metric == "read_iops_volume":
        assert pos.prometheus.get_read_iops_volume() == True
    elif metric == "read_bps_volume":
        assert pos.prometheus.get_read_bps_volume() == True
    elif metric == "write_iops_volume":
        assert pos.prometheus.get_write_iops_volume() == True
    elif metric == "write_bps_volume":
        assert pos.prometheus.get_write_bps_volume() == True
    elif metric == "read_avg_lat_volume":
        assert pos.prometheus.get_read_avg_lat_volume() == True
    elif metric == "write_avg_lat_volume":
        assert pos.prometheus.get_write_avg_lat_volume() == True
    logger.info(pos.prometheus.device_io_metric)
    assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True

T0 = {"num_vol":1,"runtime":"100","io":["write","read"]}
T1 = {"num_vol":256,"runtime":"100","io":["randwrite","randread"]}
T2 = {"num_vol":1,"runtime":"36000","io":["randwrite","randread"]}
T3 = {"num_vol":1,"unmount" : True,"runtime":"100","io":["write","read"]}
testcases = [T0,T1,T2,T3]
@pytest.mark.parametrize("testcase",testcases)
def test_volume_io_metrics(array_fixture,testcase):
    pos = array_fixture
    arrays =  array_and_volume_creation(pos=pos,num_vol=testcase["num_vol"],run_io=False)
    nvme_devs = nvme_connect(pos=pos)[1]
    fio_cmd = "fio --name=fio --ioengine=libaio --rw={} --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime={} --verify=md5"
    out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                  fio_user_data=fio_cmd.format(testcase["io"][0],testcase["runtime"]), run_async=True)
    assert pos.prometheus.publish_io_metrics() == True
    assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True
    if "unmount" in testcase.keys():
        assert pos.cli.array_unmount(array_name=arrays[0])[0] == True
    out, async_io = pos.client.fio_generic_runner(nvme_devs,
                                                  fio_user_data=fio_cmd.format(testcase["io"][1],testcase["runtime"]), run_async=True)
    assert pos.prometheus.publish_io_metrics() == True
    assert wait_sync_fio([], nvme_devs, None, async_io, sleep_time=10) == True