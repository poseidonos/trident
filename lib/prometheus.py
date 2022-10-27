from enum import Enum
from prometheus_api_client import *
import logger
from re import compile
from cli import Cli

logger = logger.get_logger(__name__)

class paths():
    pos_prometheus = '/etc/pos/pos-prometheus.yml'

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
    


        

    
          
