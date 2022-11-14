from enum import Enum
from prometheus_api_client import *
import logger
from re import T, compile
from cli import Cli

logger = logger.get_logger(__name__)

class paths():
    pos_prometheus = '/etc/pos/pos-prometheus.yml'
array_states = {
    '0' : 'NOT_EXIST',
    '1' : 'EXIST_NORMAL',
    '2' : 'EXIST_DEGRADED',
    '3' : 'BROKEN',
    '4' : 'TRY_MOUNT',
    '5' : 'TRY_UNMOUNT',
    '6' : 'NORMAL',
    '7' : 'DEGRADED', 
    '8' : 'REBUILD'
  
}
volume_states = {
    '0' : 'unmounted',
    '1' : 'mounted',
    '2' : 'offline'

}
     
class Prometheus(Cli):
    """class to navigate in prometheus DB"""

    def __init__(self, con, data_dict: dict, array_name: str = "array1"):
        """con : ssh obj of the target"""
        super().__init__(con, data_dict, array_name)
        assert self.pos_exporter(operation = "start")[0] == True
        self.prometheus_path = paths.pos_prometheus
        self.ssh_obj = con
        assert self.update_config() == True
        url = f'http://{self.ssh_obj.hostname}:2113'
        self.prom = PrometheusConnect(url=url)
        self.devicePowerOnHour = {}
        self.devicePowerCycle = {}
        self.deviceUnsafeShutdowns = {}
        self.telemetryDeviceInfo = {}
        self.deviceControllerBusyTime = {}
        self.result = {'temperature' : '',}
        

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

    
    def get_all_metrics(self) -> bool:
        """method to list all the metric info"""
        try:
            self.promlist = self.prom.all_metrics()
            return True
        except Exception as e:
            logger.error(e)
            return False
    
    def get_used_array_capacity(self, array_id) -> bool:
        """method to verify used array_capacity"""
        return [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='array_capacity_used') if array_id == item['metric']['array_id']][0]
        

    def get_total_array_capacity(self, array_id) -> bool:
        """method to verify used array_capacity"""
        return [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='array_capacity_total') if array_id == item['metric']['array_id']][0]
        
    
    def get_array_state(self, uniqueid) -> bool:
        """method to get array state"""
        state = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='array_status') if uniqueid == item['metric']['array_unique_id']][0]
        return array_states[state]
       
    def get_power_on_hour(self, device_name) -> bool:
        """method to get power on hour(upper and lower"""
        power_on_hour_lower = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_on_hour_lower') if device_name == item['metric']['nvme_ctrl_id']][0]
        power_on_hour_upper = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_on_hour_upper') if device_name == item['metric']['nvme_ctrl_id']][0]
        self.devicePowerOnHour[device_name] = {"upper" : power_on_hour_upper, "lower" : power_on_hour_lower}
        return True

    def get_power_on_cycle(self, device_name) -> bool:
        """method to get power cycle"""
        power_lower = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_cycle_lower') if device_name == item['metric']['nvme_ctrl_id']][0]
        power_upper = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='power_cycle_upper') if device_name == item['metric']['nvme_ctrl_id']][0]
        self.devicePowerCycle[device_name] = {"upper" : power_upper, "lower" : power_lower}
        return True

    def get_controller_busy_time(self, device_name) -> bool:
        """method to get power cycle"""
        busy_lower = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='controller_busy_time_lower') if device_name == item['metric']['nvme_ctrl_id']][0]
        busy_upper = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='controller_busy_time_upper') if device_name == item['metric']['nvme_ctrl_id']][0]
        self.deviceControllerBusyTime[device_name] = {"upper" : busy_upper, "lower" : busy_lower}
        return True

    def get_unsafe_shutdowns(self, device_name) -> bool:
        """method to get unsafeshutdownscycle"""
        power_lower = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='unsafe_shutdowns_lower') if device_name == item['metric']['nvme_ctrl_id']][0]
        power_upper = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='unsafe_shutdowns_upper') if device_name == item['metric']['nvme_ctrl_id']][0]
        self.deviceUnsafeShutdowns[device_name] = {"upper" : power_upper, "lower" : power_lower}
        return True

    
    def get_temperature(self, device_name) -> bool:
        """method to get unsafeshutdownscycle"""
        self.result['temperature'] = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='temperature') if device_name == item['metric']['nvme_ctrl_id']][0]
        self.telemetryDeviceInfo[device_name] = self.result
        return True
    def get_avaliable_spare(self, device_name) -> bool:
        """method to get avaliable spare infor"""
        self.result['spare_info'] =    [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='available_spare') if device_name == item['metric']['nvme_ctrl_id']][0] 
        self.telemetryDeviceInfo[device_name] = self.result
        return True

    def get_avaliable_sparethreshold(self, device_name) -> bool:
        """method to get avaliable spare infor"""
        self.result['spare_threshold'] =    [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='available_spare_threshold') if device_name == item['metric']['nvme_ctrl_id']][0] 
        self.telemetryDeviceInfo[device_name] = self.result
        return True
    
    def get_percentage_used(self, device_name) -> bool:
        """method to get percentage used in device"""
        self.result['percentusage'] = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='percentage_used') if device_name == item['metric']['nvme_ctrl_id']][0] 
        self.telemetryDeviceInfo[device_name] = self.result
        return True
    
        
    def get_critical_tempraturetime(self, device_name) -> bool:
        """method to get critical temperature time"""
        self.result['critical_temperature'] = [item['value'][1] for item in self.prom.get_current_metric_value(metric_name='critical_temperature_time') if device_name == item['metric']['nvme_ctrl_id']][0] 
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
        return True

    def publish_IO_metrics(self) -> bool:
        """method to publish IO METRIC data"""
        metric_data = ['read_bps_device', 'read_iops_device', 'write_bps_device', 'write_iops_device']
        #TODO verify the publshed data
        logger.info("currently only data is published as no verification point is set")
        for metric in metric_data:
            data = self.prom.get_current_metric_value(metric_name=metric)
            logger.info(data)
        return True

          


