#
#   BSD LICENSE
#   Copyright (c) 2021 Samsung Electronics Corporation
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions
#   are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#        the documentation and/or other materials provided with the
#        distribution.
#      * Neither the name of Samsung Electronics Corporation nor the names of
#        its contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import time
from node import SSHclient
from cli import Cli
from target_utils import TargetUtils
from utils import Client
from json import load
from os import path
from sys import exit
import logger
import pathlib
import inspect


logger = logger.get_logger(__name__)

# TODO add support for multi initiaor client object


class POS:
    """Class  object contains object for
    1, cli.py
    2, target_utils.py
    3, Client.py
    Args:
        data_path : path of pos_config data json | default = None if None read from testcase/config_files/pos_config.json
        config_path : path of toplogy file | default = None
    """

    def __init__(self, data_path=None, config_path=None):

        if data_path is None:
            data_path = "pos_config.json"
        if config_path is None:
            config_path = "topology.json"

        caller_file = inspect.stack()[1].filename
        caller_dir = pathlib.Path(caller_file).parent.resolve()
        is_file_exist = path.exists("{}/config_files/{}".format(caller_dir, data_path))
        
        if is_file_exist:
            data_path = "{}/config_files/{}".format(caller_dir, data_path)
            self.data_dict = self._json_reader(data_path, abs_path=True)[1]
        else:
            self.data_dict = self._json_reader(data_path)[1]
        self.config_dict = self._json_reader(config_path)[1]

        self.target_ssh_obj = SSHclient(
            self.config_dict["login"]["target"]["ip"],
            self.config_dict["login"]["target"]["username"],
            self.config_dict["login"]["target"]["password"],
        )
        self.cli = Cli(
            self.target_ssh_obj,
            data_dict=self.data_dict,
            pos_path=self.config_dict["login"]["paths"]["pos_path"],
        )
        self.target_utils = TargetUtils(
            self.target_ssh_obj,
            self.data_dict,
            self.config_dict["login"]["paths"]["pos_path"],
        )

        self.client = Client(
            self.config_dict["login"]["initiator"]["ip"],
            self.config_dict["login"]["initiator"]["username"],
            self.config_dict["login"]["initiator"]["password"],
        )

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

    def exit_handler(self, expected=False):
        """method to exit out of a test script as per the the result"""

        try:

            assert self.target_utils.helper.check_system_memory() == True

            if self.client.ctrlr_list()[1] is not None:
                assert (
                    self.client.nvme_disconnect(self.target_utils.ss_temp_list) == True
                )

            if expected == False:
                raise Exception(" Test case failed ! Creating core dump and clean up")
            if self.target_utils.helper.check_pos_exit() == False:
                self.cli.wbt_flush()[0] == True
                self.cli.stop_system(grace_shutdown=False)

        except Exception as e:

            logger.error(e)
            logger.info(
                "------------------------------------------ CLI HISTORY ------------------------------------------"
            )
            for cli_cmd in self.cli.cli_history:
                logger.info(cli_cmd)

            logger.info(
                "-------------------------------------------------------------------------------------------------------"
            )
            # time.sleep(10000)
            # self.cli.core_dump()
            self.cli.stop_system(grace_shutdown=False)

            assert 0
