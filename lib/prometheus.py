"""
BSD LICENSE

Copyright (c) 2021 Samsung Electronics Corporation
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.
  * Neither the name of Samsung Electronics Corporation nor the names of
    its contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from enum import Enum
from prometheus_api_client import *
import logger
from re import T, compile
from cli import Cli

logger = logger.get_logger(__name__)


class paths():
    pos_prometheus = '/etc/pos/pos-prometheus.yml'


array_states = {
    '0': 'NOT_EXIST',
    '1': 'EXIST_NORMAL',
    '2': 'EXIST_DEGRADED',
    '3': 'FAULT',
    '4': 'TRY_MOUNT',
    '5': 'TRY_UNMOUNT',
    '6': 'NORMAL',
    '7': 'DEGRADED',
    '8': 'REBUILDING'

}
volume_states = {
    '0': 'unmounted',
    '1': 'mounted',
    '2': 'offline'
}


class Prometheus(Cli):
    """class to navigate in prometheus DB"""

    def __init__(self, con, data_dict: dict, array_name: str = "array1"):
        """con : ssh obj of the target"""
        super().__init__(con, data_dict, array_name)
        assert self.pos_exporter(operation="start")[0] == True
        self.prometheus_path = paths.pos_prometheus
        self.ssh_obj = con
        if self.check_pos_exporter() == False:
            logger.info("Starting the pos-exporter as it is not runing")
            assert self.pos_exporter(operation="start")[0] == True
            assert self.check_pos_exporter() == True, "POS exporter is not running!"
        assert self.update_config() == True
        url = f'http://{self.ssh_obj.hostname}:2113'
        self.prom = PrometheusConnect(url=url)
        self.array_states = array_states
        self.volume_states = volume_states
        self.devicePowerOnHour = {}
        self.devicePowerCycle = {}
        self.deviceUnsafeShutdowns = {}
        self.telemetryDeviceInfo = {}
        self.deviceControllerBusyTime = {}
        self.result = {}
        self.device_io_metric = {}
        self.network_io_metric = {}
        self.volume_io_metric = {}
        self.result = {'temperature' : '',}
        
    def check_pos_exporter(self) -> str:
        cmd = 'systemctl is-active pos-exporter.service'
        out = self.ssh_obj.execute(cmd, get_pty=True)
        logger.info(out)
        if "active" in out[0]:
            logger.info("POS-Exporter IS RUNNING")
            return True
        else:
            logger.warning("POS-Exporter IS NOT RUNNING")
            return False

    def config_check(self) -> bool:
        """verify if targetip is updated in pos-prometheus.yml"""
        logger.info("Reading current config")
        cmd = f'cat {self.prometheus_path}'
        self.tout = self.ssh_obj.execute(cmd)
        logger.info(''.join(self.tout))
        flag = [item for item in self.tout if self.ssh_obj.hostname in item]
        if len(flag) > 0:
            logger.info("config details already updated")
            return True

    def update_config(self) -> bool:
        """method to change IP details [localhost > targetip]"""
        try:
            if self.config_check() == False:
                pattern = compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
                ip_list = []
                for out in self.tout:
                    reout = pattern.search(out)
                    if reout != None:
                        ip_list.append(reout[0])
                for ip in ip_list:
                    sed_cmd = f'sed -i "s|{ip}|{self.ssh_obj.hostname}|" /etc/pos/pos-prometheus.yml'
                    self.ssh_obj.execute(sed_cmd)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def set_telemetry_configs(self) -> bool:
        """method to start and do set-property in telemetry"""
        assert self.start_telemetry()[0] == True
        assert self.set_property()[0] == True
        assert self.get_property()[0] == True
        return True

    def docker_restart(self):
        cmd = "sudo docker restart pos-prometheus"
        out = self.ssh_obj.execute(cmd)
        return len(out)

    def get_all_metrics(self) -> bool:
        """method to list all the metric info"""
        self.promlist = self.prom.all_metrics()
        return True

    def verify_metric_values(self, metric_value, actual_value):
        """Method to verify the metric values"""
        assert metric_value == actual_value

    def get_used_array_capacity(self, array_id) -> bool:
        """method to verify used array_capacity"""
        return [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='array_capacity_used') if
                str(array_id) == item['metric']['array_id']][0]

    def get_total_array_capacity(self, array_id) -> bool:
        """method to verify used array_capacity"""
        return [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='array_capacity_total') if
                str(array_id) == item['metric']['array_id']][0]

    def get_array_state(self, uniqueid) -> bool:
        """method to get array state"""
        states = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='array_status') if
                  str(uniqueid) == item['metric']['array_unique_id']]
        if len(states):
            return states[0]
        else:
            logger.info("No matching unique id")
            assert False

    def get_volume_state(self, array_name, volume_name):
        """Method to get the volume state"""
        return [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='volume_state') if
                array_name == item['metric']['array_name'] and volume_name == item['metric']['volume_name']][0]

    def get_volume_capacity_total(self, array_name, volume_name):
        """Method to get total volume capacity"""
        return [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='volume_capacity_total') if
                array_name == item['metric']['array_name'] and volume_name == item['metric']['volume_name']][0]

    def get_volume_capacity_used(self, array_id, volume_id):
        '''Method to get volume used'''
        logger.info(self.prom.get_current_metric_value(metric_name='volume_usage_blk_cnt'))
        logger.info(
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='volume_usage_blk_cnt') if
             volume_id == item['metric']['volume_id']])
        return [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='volume_usage_blk_cnt') if
                volume_id == item['metric']['volume_id']][0]

    def get_uptime_sec(self) -> bool:
        """Method to get the uptime sec"""
        uptime_sec = \
            [item['value'][1] for item in
             self.prom.get_current_metric_value(metric_name='common_process_uptime_second')][0]
        return uptime_sec

    def get_power_on_hour(self, device_name) -> bool:
        """method to get power on hour(upper and lower"""
        power_on_hour_lower = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_on_hour_lower') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        power_on_hour_upper = [
            item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_on_hour_upper') if
            device_name == item['metric']['nvme_ctrl_id']][0]
        self.result['powerOnHours'] = str(int(power_on_hour_upper + power_on_hour_lower))
        self.telemetryDeviceInfo[device_name] = self.result

        return True

    def get_power_on_cycle(self, device_name) -> bool:
        """method to get power cycle"""
        power_lower = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_cycle_lower') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        power_upper = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_cycle_upper') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.result['powerCycles'] = str(int(power_upper + power_lower))
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_controller_busy_time(self, device_name) -> bool:
        """method to get controller_busy_time"""
        busy_lower = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='controller_busy_time_lower')
             if
             device_name == item['metric']['nvme_ctrl_id']][0]
        busy_upper = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='controller_busy_time_upper')
             if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.result['controllerBusyTime'] = str(int(busy_upper + busy_lower))
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_unsafe_shutdowns(self, device_name) -> bool:
        """method to get unsafeshutdownscycle"""
        power_lower = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='unsafe_shutdowns_lower') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        power_upper = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='unsafe_shutdowns_upper') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.result['unsafeShutdowns'] = str(int(power_upper + power_lower))
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_temperature(self, device_name) -> bool:
        """method to get temperature"""
        self.result['currentTemperature'] = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='temperature') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_avaliable_spare(self, device_name) -> bool:
        """method to get avaliable spare infor"""
        self.result['availableSpare'] = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='available_spare') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_avaliable_sparethreshold(self, device_name) -> bool:
        """method to get avaliable spare threshold"""
        self.result['availableSpareThreshold'] = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='available_spare_threshold') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_percentage_used(self, device_name) -> bool:
        """method to get percentage used in device"""
        self.result['lifePercentageUsed'] = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='percentage_used') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_critical_tempraturetime(self, device_name) -> bool:
        """method to get critical temperature time"""
        self.result['criticalTemperatureTime'] = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='critical_temperature_time') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_warning_tempraturetime(self, device_name) -> bool:
        """method to get warning temperature time"""
        self.result['warningTemperatureTime'] = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='warning_temperature_time') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_unrecoverable_MediaErrors(self, device_name) -> bool:
        """method to get unrecoverable Media Errors"""
        soft_media_error_lower = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='soft_media_error_lower') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        soft_media_error_upper = \
            [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='soft_media_error_upper') if
             device_name == item['metric']['nvme_ctrl_id']][0]
        self.result['unrecoverableMediaErrors'] = str(int(soft_media_error_upper + soft_media_error_lower))
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_smart_stats(self, device_name) -> bool:
        assert self.get_critical_tempraturetime(device_name=device_name) == True
        assert self.get_percentage_used(device_name=device_name) == True
        assert self.get_avaliable_spare(device_name=device_name) == True
        assert self.get_avaliable_sparethreshold(device_name=device_name) == True
        assert self.get_temperature(device_name=device_name) == True
        assert self.get_power_on_cycle(device_name=device_name) == True
        assert self.get_power_on_hour(device_name=device_name) == True
        assert self.get_controller_busy_time(device_name=device_name) == True
        assert self.get_unsafe_shutdowns(device_name=device_name) == True
        assert self.get_warning_tempraturetime(device_name=device_name) == True
        assert self.get_unrecoverable_MediaErrors(device_name=device_name) == True
        return True

    def get_read_iops_device(self):
        self.device_io_metric['read_iops_device'] = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='read_iops_device')]
        return True

    def get_read_bps_device(self):
        self.device_io_metric['read_bps_device'] = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='read_bps_device')]
        return True

    def get_write_iops_device(self):
        self.device_io_metric['write_iops_device'] = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='write_iops_device')]
        return True

    def get_write_bps_device(self):
        self.device_io_metric['write_bps_device'] = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='write_bps_device')]
        return True

    def publish_device_metric(self):
        assert self.get_read_iops_device() == True
        assert self.get_read_bps_device() == True
        assert self.get_write_bps_device() == True
        assert self.get_write_iops_device() == True
        return True

    def get_read_iops_network(self):
        self.network_io_metric['read_iops_network'] = [item['value'][1] for item in
                                                     self.prom.get_current_metric_value(metric_name='read_iops_network')]
        return True

    def get_read_bps_network(self):
        self.network_io_metric['read_bps_network'] = [item['value'][1] for item in
                                                     self.prom.get_current_metric_value(metric_name='read_bps_network')]
        return True

    def get_write_iops_network(self):
        self.network_io_metric['write_iops_network'] = [item['value'][1] for item in
                                                     self.prom.get_current_metric_value(metric_name='write_iops_network')]
        return True

    def get_write_bps_network(self):
        self.network_io_metric['write_bps_network'] = [item['value'][1] for item in
                                                           self.prom.get_current_metric_value(metric_name='write_bps_network')]
        return True

    def publish_network_metrics(self):
        assert self.get_read_iops_network() == True
        assert self.get_read_bps_network() == True
        assert self.get_write_iops_network() == True
        assert self.get_write_bps_network() == True
        return True

    def get_read_iops_volume(self):
        self.volume_io_metric['read_iops_volume'] = [item['value'][1] for item in
                                                           self.prom.get_current_metric_value(metric_name='read_iops_volume')]
        return True

    def get_read_bps_volume(self):
        self.volume_io_metric['read_iops_volume'] = [item['value'][1] for item in
                                                          self.prom.get_current_metric_value(metric_name='read_iops_volume')]
        return True

    def get_write_iops_volume(self):
        self.volume_io_metric['write_iops_volume'] = [item['value'][1] for item in
                                                          self.prom.get_current_metric_value( metric_name='write_iops_volume')]
        return True

    def get_write_bps_volume(self):
        self.volume_io_metric['write_bps_volume'] = [item['value'][1] for item in
                                                          self.prom.get_current_metric_value(metric_name='write_bps_volume')]
        return True

    def get_read_avg_lat_volume(self):
        self.volume_io_metric['read_avg_lat_volume'] = [item['value'][1] for item in
                                                          self.prom.get_current_metric_value(
                                                              metric_name='read_avg_lat_volume')]
        return True

    def get_write_avg_lat_volume(self):
        self.volume_io_metric['write_avg_lat_volume'] = [item['value'][1] for item in
                                                             self.prom.get_current_metric_value(
                                                                 metric_name='write_avg_lat_volume')]
        return True

    def publish_volume_io_metrics(self):
        assert self.get_read_iops_volume() == True
        assert self.get_read_bps_volume() == True
        assert self.get_write_iops_volume() == True
        assert self.get_write_bps_volume() == True
        assert self.get_read_avg_lat_volume() == True
        assert self.get_write_avg_lat_volume() == True
        return True

    def publish_io_metrics(self):
        assert self.publish_device_metric() == True
        time.sleep(20)
        assert self.publish_network_metrics() == True
        time.sleep(20)
        assert self.publish_volume_io_metrics()
        return True

