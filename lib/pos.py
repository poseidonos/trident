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

import time
from node import SSHclient
from cli import Cli
from target_utils import TargetUtils
from pos_config import POS_Config
from utils import Client
from prometheus import Prometheus
from json import load
from os import path
from sys import exit
import logger
import pathlib
import inspect
from copy import deepcopy
from threadable_node import threaded

logger = logger.get_logger(__name__)

# TODO add support for multi initiaor client object

Max_Client_Cnt = 256  # Maximum number of client that can connect


class POS:
    """Class  object contains object for
    1, cli.py
    2, target_utils.py
    3, utils.py
    Args:
        data_path : path of pos_config data json | default = None if None read from testcase/config_files/pos_config.json
        config_path : path of toplogy file | default = None
    """

    def __init__(self, data_path=None, config_path=None):

        if data_path is None:
            data_path = "pos_config.json"
        if config_path is None:
            config_path = "topology.json"
        trident_config = "trident_config.json"
        self.client_cnt = 0
        self.client_handle = []
        self.obj_list = []

        caller_file = inspect.stack()[1].filename
        caller_dir = pathlib.Path(caller_file).parent.resolve()
        is_file_exist = path.exists("{}/config_files/{}".format(caller_dir, data_path))

        if is_file_exist:
            data_path = "{}/config_files/{}".format(caller_dir, data_path)
            self.data_dict = self._json_reader(data_path, abs_path=True)[1]
        else:
            self.data_dict = self._json_reader(data_path)[1]

        self.data_dict_bkp = deepcopy(self.data_dict)

        self.config_dict = self._json_reader(config_path)[1]
        self.trident_config = self._json_reader(trident_config)[1]
        self.pos_as_service = self.trident_config["pos_as_a_service"]["enable"]

        self.client_fio_conf = self.trident_config["forced_fio_config"]

        logger.info(f"Installed POS as Service : {self.pos_as_service}")
       
        self.target_ssh_obj = SSHclient(
            self.config_dict["login"]["target"]["server"][0]["ip"],
            self.config_dict["login"]["target"]["server"][0]["username"],
            self.config_dict["login"]["target"]["server"][0]["password"],
        )
        self.obj_list.append(self.target_ssh_obj)
        pos_path = None
        if not self.pos_as_service:
            pos_path = self.config_dict["paths"]["pos_path"]

        self.cli = Cli(self.target_ssh_obj, data_dict=self.data_dict,
                       pos_as_service=self.pos_as_service,
                       pos_source_path=pos_path)

        self.target_utils = TargetUtils(self.target_ssh_obj, self.cli,
                                        self.data_dict,
                                        pos_as_service=self.pos_as_service)
         
        self.pos_conf = POS_Config(self.target_ssh_obj)
        self.pos_conf.load_config()
        if self.pos_as_service:
            self.prometheus = Prometheus(self.target_ssh_obj, self.data_dict)

        self.client_cnt = self.config_dict["login"]["initiator"]["number"]
        if self.client_cnt >= 1 and self.client_cnt < Max_Client_Cnt:
            for client_cnt in range(self.client_cnt):
                self.create_client_objects(client_cnt)
        else:
            assert 0

        self.collect_pos_core = False # Don't collect core after test fail

    def create_client_objects(self, client_cnt):
        client_list = self.config_dict["login"]["initiator"]["client"]
        ip = client_list[client_cnt]["ip"]
        username = client_list[client_cnt]["username"]
        password = client_list[client_cnt]["password"]
        client_ssh_obj = SSHclient(ip, username, password)
        self.obj_list.append(client_ssh_obj)
        client_obj = Client(client_ssh_obj)
        client_obj.set_fio_runtime(self.client_fio_conf)

        self.client_handle.append(client_obj)

        if self.client_cnt == 1:
            self.client = self.client_handle[0]
        
    def _clearall_objects(self):
        if len(self.obj_list) > 0:
            for obj in self.obj_list:
                obj.close()
        return True

    def _json_reader(self, json_file: str, abs_path=False) -> dict:
        """reads json file from /testcase/config_files

        Read the config file from following location:
        Args:
            json_file (str) json name [No path required]
        """
        try:
            if abs_path:
                json_path = json_file
            else:
                dir_path = path.dirname(path.realpath(__file__))
                json_path = f"{dir_path}/../testcase/config_files/{json_file}"

            logger.info(f"reading json file {json_path}")
            with open(f"{json_path}") as f:
                json_out = load(f)
            f.close()
            return True, json_out
        except OSError as e:
            logger.error(f" failed to read {json_file} due to {e}")
            exit()

    def set_core_collection(self, collect_pos_core: bool = False):
        """ Method is to eable core collection on test failure """
        self.collect_pos_core = collect_pos_core

    def collect_core(self, is_pos_running: bool):
        """ Method to collect pos log and core dump """ 
        try:
            if is_pos_running:
                assert self.target_utils.dump_core() == True
            return True
        except Exception as e:
            logger.error("Failed to collect core data due to {e}")
            return False

    def exit_handler(self, expected=False, hetero_setup=False, dump_cli=True):
        """ Method to exit out of a test script as per the the result """
        try:
            assert self.target_utils.helper.check_system_memory() == True
        
            if dump_cli:
                self.cli.dump_cli_history(clean=True)

            is_pos_running = False
            if self.target_utils.helper.check_pos_exit() == False:
                is_pos_running = True
            
            # POS Client Cleanup
            for client in self.client_handle:
                assert client.reset(pos_run_status=is_pos_running) == True

            # If system stat is not expected and core collection in enable
            if expected == False and is_pos_running == True:
                logger.error("Test case failed!")
                if self.collect_pos_core:
                    logger.error("Creating core dump")
                    assert self.target_utils.dump_core() == True
                else:
                    logger.error("System clean up")
                    self.cli.pos_stop(grace_shutdown=False)
            if expected == True and is_pos_running == True:
                logger.error("System clean up")
                self.cli.pos_stop(grace_shutdown=False)

            # Reset the target to previous state
            self.pos_conf.restore_config()

            if hetero_setup and not is_pos_running:
                if not self.target_utils.hetero_setup.reset():
                    raise Exception("Failed to reset the target state")

            if expected == False:
                assert 0
        except Exception as e:
            logger.error(e)
            assert 0
