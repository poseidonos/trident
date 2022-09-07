#
#    BSD LICENSE
#    Copyright (c) 2021 Samsung Electronics Corporation
#    All rights reserved.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions
#    are met:
#
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in
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
import logger
import utils
import helper
import json
import pprint
from datetime import timedelta
from threading import Thread
from threading import Lock


logger = logger.get_logger(__name__)


class Cli:
    """
    The Cli class contains objects for  POS cli

    Args:
        con (object) : target ssh obj
        data_dict (dict) : pos_config details from testcase/config_files/`.json
         pos_path (str) : path for pos source
        array_name (str) : name of the POS array
    """

    def __init__(
        self, con, data_dict: dict, pos_path: str, array_name: str = "POSARRAY1"
    ):
        self.ssh_obj = con
        self.helper = helper.Helper(con)
        self.data_dict = data_dict
        self.pos_path = pos_path
        self.array_name = array_name
        self.new_cli_path = "/bin/poseidonos-cli"  ##path of POS cli
        self.array_info = {}
        self.cli_history = []
        self.lock = Lock()

    def run_cli_command(
        self, command: str, command_type: str = "request", timeout=30
    ) -> (bool, dict()):
        """
        Method to Execute CLI commands and return Response
        Args:

            command (str):  cli command to be executed
            command_type (str) : Command type [array, device, system, qos, volume]
            timeout (int) : time in seconds to wait for compeltion |default 30 seconds as max time allowed time is 30 sec wait
        """

        try:
            retry_cnt = 1
            cmd = "{}{} {} {} --json-res".format(
                self.pos_path, self.new_cli_path, command_type, command
            )
            start_time = time.time()
            run_end_time = start_time + timeout

            while time.time() < run_end_time:
                listout = self.ssh_obj.execute(cmd, get_pty=True)
                
                elapsed_time_secs = time.time() - start_time
                logger.info(
                    "Command execution completed in : {} secs".format(
                        timedelta(seconds=elapsed_time_secs)
                    )
                )
                out = "".join(listout)
                if "cannot connect to the PoseidonOS server" in out:
                    logger.warning(
                        "POS is not running! Please start POS and try again!"
                    )
                    return False, out
                elif "invalid data metric" in out:
                    logger.warning("Invalid syntax passed to the command ")
                    return False, out
                elif "invalid json file" in out:
                    logger.error("Passed file contains invalid json data")
                    return False, out
                elif "Receiving error" in out:
                    logger.error("POS crashed in between! please check POS logs")
                    return False, out
                
                else:

                    if "volume mount" in cmd :
                        out = listout[1] if len(listout) > 1 else "".join(listout)
                                             
                
                parse_out = self.parse_out(out, cmd)
                self.add_cli_history(parse_out)

                if parse_out["status_code"] == 0:
                    return True, parse_out
                elif parse_out["status_code"] == 1030:
                    logger.info(
                        "Poseidonos is in Busy state, status code is {}. \
                        Command retry count is {}".format(
                            parse_out["status_code"], retry_cnt
                        )
                    )
                    retry_cnt += 1
                    time.sleep(5)
                    continue
                else:
                    return False, parse_out
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False, None

    def add_cli_history(self, parse_out: dict) -> bool:
        """
        Method to get cli command history for debugging
        """
        if len(self.cli_history) > 100000:
            del self.cli_history[0]

        self.cli_history.append(
            [parse_out["command"], parse_out["status_code"], parse_out["description"]]
        )
        return True

    def parse_out(self, jsonout, command):
        
        out = json.loads(jsonout)
        command = command
        if "param" in out.keys():
            param = out["Request"]["param"]
        else:
            param = {}
        logger.info(pprint.pformat(out))
        status_code = out["Response"]["result"]["status"]["code"]
        description = out["Response"]["result"]["status"]["description"]
        """
        logger.info(
            "status code response from the command {} is {}".format(
                command, status_code
            )
        )
        logger.info("DESCRIPTION from command {} is {}".format(command, description))
        """
        # logger.info("status code response from the command {} is {}".format(command, status_code))
        # logger.info("DESCRIPTION from command {} is {}".format(command, description))

        data = None
        if "data" in out["Response"]["result"]:
            data = out["Response"]["result"]["data"]

        return {
            "output": out,
            "command": command,
            "status_code": status_code,
            "description": description,
            "data": data,
            "params": param,
        }

    def _get_pos_logs(self):
        """
        method to get pos logs.. creates a thread to tail logs from /scripts/pos.log
        """
        while True:
            out = self.start_out.get_output()
            if out:
                logger.info(out)
            else:
                pass
    
    #####################################################system################################
    def start_system(self) -> (bool, dict()):
        """
        Method to start pos
        """
        try:
            out = ""
            """
            max_running_time = 30 * 60 #30min
            start_time = time.time()
            self.out = self.ssh_obj.run_async("nohup {}/bin/{} >> {}/script/pos.log".format(self.pos_path, "poseidonos", self.pos_path))
            while True:
                logger.info("waiting for POS logs")
                time.sleep(5)
                if self.out.is_complete() is False:
                    logger.info("Time-consuming : {}".format(time.time() - start_time))
                    return True, out
                cur_time = time.time()
                running_time = cur_time - start_time
                if running_time > max_running_time:
                    return False, out

            """
            # to use the CLI to start the
            cli_error, jout = self.run_cli_command("start", command_type="system")
            if cli_error == True:
              return True, jout
              
        except Exception as e:
            logger.error(f"failed due to {jout}")
            return False, jout

    def stop_system(
        self,
        grace_shutdown: bool = True,
        time_out: int = 300,
    ) -> (bool, dict()):
        """
        Method to stop poseidon
        Args:
            grace_shutdown (bool) :"flag to kill POS grace_fully" (optional) | (default= True),
            time_out (int) "timeout to wait POS map" (optional) | (default =300)
        """
        try:
            out = None
            if grace_shutdown:
                assert self.list_array()[0] == True
                array_list = list(self.array_dict.keys())
                if len(array_list) == 0:
                    logger.info("No array found in the config")
                else:
                    for array in array_list:
                        # assert self.info_array(array_name=array)[0] == True

                        if self.array_dict[array].lower() == "mounted":
                            assert self.unmount_array(array_name=array)[0] == True

                out = self.run_cli_command("stop --force", command_type="system")
                if out[0] == False:
                    logger.error("POS system stop command failed.")
                    return False, out

                if out[1]["output"]["Response"]["result"]["status"]["code"] != 0:
                    logger.error("POS graceful shutdown failed.")
                    return False, out

                logger.info("POS graceful shutdown successful. Verifying PID...")
                count = 0
                while True:
                    out = self.helper.check_pos_exit()
                    if out == False:
                        logger.warning("POS PID is still active")
                        time.sleep(10)
                        count += 10
                    else:
                        break

                if count == time_out:
                    logger.error(f"POS PID is still active after {count} seconds.")
                    return False, out
            else:
                out = self.ssh_obj.execute(command="pkill -9 pos")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            # self.stop_system(grace_shutdown=False)
            return False, out
        return True, out

    def setposproperty_system(self, rebuild_impact: str) -> (bool, dict()):
        """
        method to set the rebuild impact
        Args:
            Rebuild_impact (str) : rebuild weight
        """
        try:
            cmd = "set-property --rebuild-impact {}".format(rebuild_impact)
            cli_error, jout = self.run_cli_command(cmd, command_type="system")
            if cli_error == True:
                return True, jout
                
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def info_system(self) -> (bool, dict()):
        """
        method to get system info of pos
        """
        try:
            cmd = "info"
            cli_error, jout = self.run_cli_command(cmd, command_type="system")
            if cli_error == True:
                return True, jout
            
            else:
                    raise Exception(jout["description"])
           
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ################################################array#######################################
    def list_array(self) -> (bool, dict()):
        """
        Method to list array
        """
        try:
            self.array_dict = {}
            cmd = "list"
            cli_error, jout = self.run_cli_command(cmd, command_type="array")

            if cli_error == False and int(jout["status_code"]) == 1224:
                logger.info(jout["description"])
                return True, jout
            if cli_error == True:
                out = jout["output"]["Response"]
                if "There is no array" in out["result"]["data"]["arrayList"]:
                    logger.info("No arrays present in the config")
                    return True, out
                else:

                    for i in out["result"]["data"]["arrayList"]:
                        a_name = i["name"]
                        a_status = i["status"]
                        self.array_dict[a_name] = a_status
                    logger.info(
                        f"{str(len(list(self.array_dict.keys())))} Arrays are present in the Config and the Array names are {list(self.array_dict.keys())}"
                    )
                    return True, out
            else:
                raise Exception("list array command execution failed ")
        except Exception as e:
            logger.error("list array command failed with exception {}".format(e))
            return False, jout

    def create_array(
        self,
        write_buffer: str,
        data: list,
        spare: list,
        raid_type: str,
        array_name: str = None,
    ) -> (bool, dict()):

        """
        Method to create array
        Args:
            write_buffer (str) :name of the uram
            data (list) : list of the data devices
            spare (list) : list of the spare devices
            raid_type (str) : Raid type
            array_name (str) : name of the array
        """
        try:
            data = ",".join(data)
            if array_name != None:
                self.array_name = array_name

            cmd = "create -b {} -d {} -a {} ".format(
                write_buffer, data, self.array_name
            )

            if spare and raid_type != "no-raid":
                spare = spare[0] if len(spare) == 0 else ",".join(spare)
                cmd += f" --spare {spare}"
            if raid_type != "no-raid":
                cmd += f" --raid {raid_type}"
            else:
                cmd += " --no-raid"
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
               return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def mount_array(
        self, array_name: str = None, write_back: bool = True
    ) -> (bool, dict()):
        """
        Method to mount array

        Args:
            array_name (str) : name of the array
            write_back (bool)  : write through if True else write back
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "mount -a {}".format(self.array_name)
            if write_back == False:
                cmd += " --enable-write-through"
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def unmount_array(self, array_name: str = None) -> (bool, dict()):
        """
        Method to unmount array

        Args:
            array_name (str) : name of the array
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "unmount -a {} --force".format(self.array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def reset_devel(self) -> (bool, dict()):
        """
        Method to array reset
        """
        try:
            cmd = "resetmbr"
            cli_error, jout = self.run_cli_command(cmd, command_type="devel")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to  {}".format(e))
            return False, jout

    def delete_array(self, array_name: str = None) -> (bool, dict()):
        """
        Method to delete array

        Args:
            array_name (str) name of the array
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "delete -a {} --force".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def info_array(self, array_name: str = None) -> (bool, dict()):
        """
        Method to get array information

        Args:
            array_name (str) name of the array
        """
        spare_dev = []
        data_dev = []
        buffer_dev = []
        try:

            if array_name != None:
                self.array_name = array_name
            cmd = "list -a {}".format(self.array_name)
            out = self.run_cli_command(cmd, command_type="array")
            if out[0] == True:
                if out[1]["output"]["Response"]["result"]["status"]["code"] == 0:
                    flag = True
                else:
                    flag = False
            else:
                logger.warning("No array found in the config")
                return False, out[1]
            if flag == True:
                array_state = out[1]["data"]["state"]
                array_size = out[1]["data"]["capacity"]
                array_situation = out[1]["data"]["situation"]
                rebuild_progress = out[1]["data"]["rebuilding_progress"]
                for dev in out[1]["data"]["devicelist"]:
                    if dev["type"] == "DATA":
                        data_dev.append(dev["name"])
                    elif dev["type"] == "SPARE":
                        spare_dev.append(dev["name"])
                    elif dev["type"] == "BUFFER":
                        buffer_dev.append(dev["name"])
                    else:
                        logger.error("Disk type is unknown")
                        return (False, None)

            else:
                logger.error("failed to execute list_array_device command")
                return False, out[1]
            self.normal_data_disks = list(
                [dev for dev in data_dev if "REMOVED" not in dev]
            )
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False, None, None, None
        self.array_info[array_name] = {
            "state": array_state,
            "size": array_size,
            "situation": array_situation,
            "rebuilding_progress": rebuild_progress,
            "data_list": data_dev,
            "spare_list": spare_dev,
            "buffer_list": buffer_dev,
        }
        return (True, out)

    def addspare_array(
        self, device_name: str, array_name: str = None
    ) -> (bool, dict()):
        """
        Method to add spare drive

        Args:
            device_name (str) : name of the device
            array_name (str) : name of the array
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "addspare -s {} -a {}".format(device_name, self.array_name)
            cli_error, out = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                return True, out
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, out

    def rmspare_array(self, device_name: str, array_name: str = None) -> (bool, dict()):
        """
        Method to remove spare drive

        Args:
            device_name (str) : name of the device
            array_name (str) : name of the array
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "rmspare -s {} -a {}".format(device_name, array_name)
            cli_error, out = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                return True,out
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, out

    def autocreate_array(
        self,
        buffer_name: str,
        num_data: str,
        raid: str,
        array_name: str = None,
        num_spare: str = "0",
    ) -> (bool, dict()):
        """
        Method to ameutocreate array

        Args:
            array_name (str) : name of the array
            buffer_name (str) : name of the buffer
            num_data (str) : num of data devices
            num_spare (str) : num of spare | 0 if no spare
            raid (str) : type of raid
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "autocreate --array-name {} --buffer {} --num-data-devs {}".format(
                self.array_name, buffer_name, num_data
            )

            if int(num_spare) > 0:
                cmd += f" --num-spare {num_spare} "
            if raid != "no-raid":
                cmd += f" --raid {raid}"
            else:
                cmd += " --no-raid"

            cli_error, out = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                return True, out
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, out

    ########################################################device######################
    def scan_device(
        self,
    ) -> (bool, dict()):
        """
        Method to scan devices
        """
        try:
            cmd = "scan"
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def create_device(
        self,
        uram_name: str,
        bufer_size: str = None,
        strip_size: str = None,
        numa: int = None,
    ) -> (bool, dict()):
        """
        Method to create malloc device
        Args:
            uram_name (str) : Name of buffer device
            buffer_szie (str) : Buffer device size
            strip_size (str) : Size of the stripe
            numa (int) : Numa node number
        """
        try:
            for uram in self.data_dict["device"]["uram"]:
                if uram["uram_name"] == uram_name:
                    bufer_size = bufer_size or uram["bufer_size"]
                    strip_size = strip_size or uram["strip_size"]
                    numa = numa or uram["numa_node"]
                    break

            cmd = 'create --device-name {} --num-blocks {} --block-size {} --device-type "uram" --numa {}'.format(
                uram_name, bufer_size, strip_size, numa
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def list_device(self) -> (bool, dict()):
        """
        Method to list devices

        """
        try:
            cmd = "list"
            cli_error, out = self.run_cli_command(cmd, command_type="device")
            devices = []
            self.device_map = {}
            self.device_type = {}
            self.dev_type = {"NVRAM": [], "SSD": []}

            if cli_error == True:
                
                if out["description"].lower() == "no any device exists":
                        logger.info("No devices listed")
                        return True, out, devices, self.device_map, self.dev_type
                if "data" in out:
                        dev = out["data"]["devicelist"]
                        for device in dev:
                            devices.append(device["name"])
                            dev_map = {
                                "name": device["name"],
                                "addr": device["addr"],
                                "mn": device["mn"],
                                "sn": device["sn"],
                                "size": device["size"],
                                "type": device["type"],
                                "class": device["class"],
                                "numa": device["numa"],
                            }
                            if dev_map["type"] in self.dev_type.keys():
                                self.dev_type[dev_map["type"]].append(dev_map["name"])
                                self.device_map.update({device["name"]: dev_map})

                self.NVMe_BDF = self.device_map

                self.system_disks = [
                            item
                            for item in self.device_map
                            if self.device_map[item]["class"].lower() == "system"
                            and self.device_map[item]["type"].lower() == "ssd"
                        ]

                self.array_disks = [
                            item
                            for item in self.device_map
                            if self.device_map[item]["class"].lower() == "array"
                            and self.device_map[item]["type"].lower() == "ssd"
                        ]

                return (True, out)
            else:
                raise Exception(
                        "list dev command failed with status code {}".format(
                            out["status_code"]
                        )
                    )
           
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, None, None, None, None

    def smart_device(self, devicename: str) -> (bool, dict()):
        """
        method to get smart details of a devce
        Args:
            device_name : name of the device

        """
        try:
            cmd = "smart -d {}".format(devicename)
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def smart_log_device(self, devicename: str) -> (bool, dict()):
        """
        method to get smart details of a devce
        Args:
            device_name : name of the device

        """
        try:
            cmd = "smart-log -d {}".format(devicename)
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ################################################logger##############################
    def set_log_level_logger(self, level: str) -> (bool, dict()):
        """
        method to set the log level
        Args:
            level (str) : logger level
        """
        try:
            cmd = "set-level --level {}".format(level)
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
               return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def get_log_level_logger(self) -> (bool, dict()):
        """
        method to get the log level

        """

        try:
            cmd = "get-level"
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def apply_log_filter(self) -> (bool, dict()):
        """
        method to set log filter

        """
        try:
            cmd = "apply-filter"
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def info_logger(self) -> (bool, dict()):
        """
        method to get logger info

        """
        try:
            cmd = "info"
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ###################################################telemetry#########################

    def start_telemetry(self) -> (bool, dict()):
        """
        method to start telemetry

        """
        try:
            cmd = "start"
            cli_error, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def stop_telemetry(self) -> (bool, dict()):
        """
        method to stop telemetry

        """
        try:
            cmd = "stop"
            cli_error, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ###################################################QOS##############################
    def create_volume_policy_qos(
        self,
        volumename: str,
        arrayname: str,
        maxiops: str,
        maxbw: str,
        miniops: str = None,
        minbw: str = None,
    ) -> (bool, dict()):
        """
        method to create qos volume policy
        Args:
            volumename (str) : name of the volume
            arrayname (str) : name of the array
            maxiops (str) IOPs value
            maxbw (str) bandwidth
            miniops (str) |default
            minbw (str)
        Returns:
            bool, list
        """
        try:
            if miniops == None and minbw != None:
                cmd = "create -v {} -a {} --maxiops {} --maxbw {} --minbw {}".format(
                    volumename, arrayname, maxiops, maxbw, minbw
                )
            elif minbw == None and miniops != None:
                cmd = "create -v {} -a {} --maxiops {} --maxbw {} --miniops {}".format(
                    volumename, arrayname, maxiops, maxbw, miniops
                )
            else:
                cmd = "create -v {} -a {} --maxiops {} --maxbw {}".format(
                    volumename, arrayname, maxiops, maxbw
                )

            cli_error, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def reset_volume_policy_qos(
        self, volumename: str, arrayname: str
    ) -> (bool, dict()):
        """method to reset volume policy
        Args:
            volumename (str) name of the volume
            arrayname (str) name of the array

        """
        try:
            cmd = "reset -v {} -a {}".format(volumename, arrayname)
            cli_error, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def list_volume_policy_qos(self, volumename: str, arrayname: str) -> (bool, dict()):
        """
        method to list volume policy
        Args:
            volumename (str) : name of the volume
            arrayname (str) : name of the array

        """
        try:
            cmd = "list -v {} -a {}".format(volumename, arrayname)
            cli_error, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ###################################################volume#############################
    def list_volume(self, array_name: str = None) -> (bool, dict()):
        """
        Method to list volumes
        Args:
            array_name : name of the array

        """
        try:
            if array_name != None:
                self.array_name = array_name
            self.vol_dict = {}

            cmd = "list -a {}".format(self.array_name)
            cli_error, out = self.run_cli_command(cmd, command_type="volume")

            if cli_error == False:
                raise Exception("CLI Error")
            if out["status_code"] != 0:
                raise Exception(out["description"])
            no_vols_str = f"no any volume exist in {self.array_name}"
            if no_vols_str == out["description"]:
                logger.warning(out["description"])
                self.vols = []
                return True, [], {}
            for vol in out["data"]["volumes"]:
                self.vol_dict[vol["name"]] = {
                    "total": vol["total"],
                    "status": vol["status"],
                    "max_iops": vol["maxiops"],
                    "maxbw": vol["maxbw"],
                }
            self.vols = list(self.vol_dict.keys())
            return True, list(self.vol_dict.keys())
        except Exception as e:
            logger.error("list volume command failed with exception {}".format(e))
            return False, out

    def info_volume(
        self, array_name: str = None, vol_name: str = None
    ) -> (bool, dict()):
        """
        Method to get volume information

        Args:
            array_name (str) name of the array
            array_name (str) name of the volume
        """
        try:
            if array_name != None:
                self.array_name = array_name

            self.volume_info = {}
            self.volume_info[array_name] = {}

            cmd = "list -a {} -v {}".format(self.array_name, vol_name)
            out = self.run_cli_command(cmd, command_type="volume")
            if out[0] == True:
                if out[1]["output"]["Response"]["result"]["status"]["code"] == 0:
                    flag = True
                else:
                    flag = False
            else:
                logger.warning("No array found in the config")
                return False, out[1]
            if flag == True:
                self.volume_info[array_name][vol_name] = {
                    "uuid": out[1]["data"]["uuid"],
                    "name": out[1]["data"]["name"],
                    "total_capacity": out[1]["data"]["total"],
                    "status": out[1]["data"]["status"],
                    "max_iops": out[1]["data"]["maxiops"],
                    "min_iops": out[1]["data"]["miniops"],
                    "max_bw": out[1]["data"]["maxbw"],
                    "min_bw": out[1]["data"]["minbw"],
                    "subnqn": out[1]["data"]["subnqn"],
                    "array_name": out[1]["data"]["array_name"],
                }
                vol_status = self.volume_info[array_name][vol_name]["status"]
                if vol_status == "Mounted":
                    cap = out[1]["data"]["remain"]
                    self.volume_info[array_name][vol_name]["remain"] = cap
            else:
                logger.error("failed to execute list_array_device command")
                return False, out[1]
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return (False, None)

        return (True, out)

    def create_volume(
        self,
        volumename: str,
        size: str,
        array_name: str = None,
        iops: str = 0,
        bw: str = 0,
    ) -> (bool, dict()):
        """
        Method to create volume
        Args:
            volumename (str) : name of the volume
            size (str) : size of the volume
            array_name (str) : name of the array
            iops (str) : iops value
            bw (str) : bandwidth value
            #TODO add max and min iops

        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = " create -v {} --size {} --maxiops {} --maxbw {} -a {} ".format(
                volumename, size, iops, bw, array_name
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def delete_volume(self, volumename: str, array_name: str) -> (bool, dict()):
        """
        Method to delete volume
        Args:
            volumename (str) : name of the volume
            array_name (str) : name of the array

        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "delete -a {} -v {} --force ".format(self.array_name, volumename)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def mount_volume(
        self, volumename: str, array_name: str, nqn: str = None
    ) -> (bool, dict()):
        """
        Method to mount volume
        Args:
            volumename (str) name of the volume
            array_name (str) name of the array
            nqn (str) Subsystem name  |if nqn == None then random NQN will be selected by POS

        """
        try:
            cmd = "mount -v {} -a {} --force".format(volumename, array_name)
            if nqn:
                cmd += " --subnqn {}".format(nqn)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")

            if cli_error == True:
                return cli_error, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def rename_volume(
        self, new_volname: str, volname: str, array_name: str = None
    ) -> (bool, dict()):
        """
        Method to unmount volume
        Args:
            new_volname (str) name of the new volume
            volname (str) old volumename
            array_name (str) old array_name

        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "rename --volume-name {} --array-name {} --new-volume-name {}".format(
                volname, self.array_name, new_volname
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def unmount_volume(self, volumename: str, array_name: str = None) -> (bool, dict()):
        """
        Method to unmount volume
        Args:
            volumename (str) name of the volume
            array_name (str) name of array

        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "unmount -v {} -a {} --force".format(volumename, self.array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def mount_with_subsystem_volume(
        self, volumename: str, nqn_name: str, ip: str, vcid: str, array_name: str = None
    ) -> (bool, dict()):
        """
        method to mount volume with subsystem
        Args:
            volumename (str) name of the volume
            nqn_name (str) : name of the SS
            array_name (str) name of the array
            ip (str) : IP details
            vcid (str) : port details


        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "mount-with-subsystem --volume-name {} --subnqn {} --array-name {} --trtype tcp --traddr {} --trsvcid {} --force".format(
                volumename, nqn_name, self.array_name, ip, vcid
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ################################## Subsystem ##############################
    def create_subsystem(
        self,
        nqn_name: str,
        ns_count: str = None,
        serial_number: str = None,
        model_name: str = None,
    ) -> (bool, dict()):
        """
        Method to create nvmf subsystem
        Args:
            nqn_name (str) : Name of subsystem
            ns_count (int) : Max namespace supported by subsystem
            serial_number (str) : Serial number of subsystem
            model_name (str) : Model number of subsystem
        """
        try:
            subsystem = self.data_dict["subsystem"]
            ns_count = ns_count or subsystem["ns_count"]
            serial_number = serial_number or subsystem["serial_number"]
            model_name = model_name or subsystem["model_name"]

            cmd = "create --subnqn {} --serial-number {} --model-number {} \
                    --max-namespaces {} --allow-any-host".format(
                nqn_name, serial_number, model_name, ns_count
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def list_subsystem(self) -> (bool, dict()):
        """
        method executes nvmf_get_subsystems

        """
        try:
            nvmf_out, temp = {}, {}
            out = self.run_cli_command("list", command_type="subsystem")
            for data in out[1]["data"]["subsystemlist"]:
                temp = data
                nvmf_out[data["nqn"]] = temp

            return (True, nvmf_out)

        except Exception as e:
            logger.error("Get_nvmf_subsystem failed due to %s" % e)
            return (False, None)

    def add_listner_subsystem(
        self, nqn_name: str, mellanox_interface: str, port: str, transport: str = "TCP"
    ):
        """
        Method to add nvmf listner
        Args:
            nqn_name (str) : Subsystem name
            mellanox_interface
        """
        try:

            cmd = (
                "add-listener --subnqn {} --trtype {} --traddr {} --trsvcid {}".format(
                    nqn_name, transport, mellanox_interface, port
                )
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def create_transport_subsystem(
        self,
        buf_cache_size: str = 64,
        num_shared_buf: str = 4096,
        transport_type: str = "TCP",
    ) -> (bool, dict()):
        """
        Method to create transport
        Args:
            buf_cache_size (str) : buffer size for TCP packets
            num_share_buf (str) : num of buffers
            transport type (str)
        """
        try:
            command = "create-transport --trtype {} --buf-cache-size {} --num-shared-buf {} ".format(
                transport_type.upper(), buf_cache_size, num_shared_buf
            )
            cli_error, jout = self.run_cli_command(command, command_type="subsystem")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def delete_subsystem(self, nqn_name: str, force: bool = True) -> (bool, dict()):
        """method to delete subsystem
        Args:
            nqn_name (str) name of the subsystem
            force (bool) |default True

        """
        try:
            force = " --force" if force else " "
            command = f"delete --subnqn {nqn_name} {force}"
            cli_error, jout = self.run_cli_command(command, "subsystem")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")

        except Exception as e:
            logger.error(e)
            return False, jout

    # TODO check if the below Methods are to be open sourced/ renamed for open sourcing
    ######################################wbt#######################################

    def wbt_do_gc(self, array_name: str = None):
        """
        Method to do gc
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "do_gc --array {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_get_gc_status(self, array_name: str = None):
        """
        Method to get gc status
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "get_gc_status --array {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.error(jout["description"])
                    seg_info = jout["output"]["Response"]["result"]["data"]["gc"][
                        "segment"
                    ]
                    self.free_segments, self.total_segments, self.used_segments = [
                        value for value in seg_info.values()
                    ]
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_set_gc_threshold(
        self, array_name: str = None, normal: int = None, urgent: int = None
    ):
        """
        Method to set gc threshold value to the given array
        """
        try:
            if array_name == None:
                array_name = self.array_name
            if normal == None or urgent == None:
                logger.error(
                    "normal and urgent are mandatory params for set_gc_threshold"
                )
            cmd = "set_gc_threshold --array {} --normal {} --urgent {}".format(
                array_name, normal, urgent
            )
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_get_gc_threshold(self, array_name: str = None):
        """
        Method to get gc threshold
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "get_gc_threshold --array {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    threshold = jout["output"]["Response"]["result"]["data"][
                        "gc_threshold"
                    ]
                    self.gc_normal, self.gc_urgent = [
                        value for value in threshold.values()
                    ]
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_flush(self, array_name: str = None):
        """
        Method to flush
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "flush -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_read_vsamap_entry(
        self, volumename: str, rba: str, array_name: str = None
    ) -> (bool):
        """
        Method to read vsamap entry
        """
        try:
            output_txt_path = "/root/output.txt"

            if utils.Client.is_file_present(output_txt_path) == True:
                delete_cmd = "rm -fr %s" % output_txt_path
                logger.info("Deleting existing output files")
                out = self.ssh_obj.execute(delete_cmd)

            vsamap_entry_cmd = "read_vsamap_entry -v {} --rba {} -a {}".format(
                volumename, rba, array_name
            )
            cli_error, jout = self.run_cli_command(vsamap_entry_cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    if utils.Client.is_file_present(output_txt_path) == False:
                        raise Exception("output file not generated")
                    else:
                        logger.info("Output.txt file Generated!!!")
                        flag, map_dict = self.helper.wbt_parser(output_txt_path)
                        if flag == True:
                            logger.info(
                                "Successfully data parsed from output.txt file "
                            )
                            return map_dict
                        else:
                            raise Exception("Failed to parse data from output.txt file")
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_read_stripemap_entry(self, vsid: str, array_name: str = None):
        """
        Method to read stripe map entry
        """
        try:
            logger.info("Executing read_stripemap_entry command")
            output_txt_path = "/root/output.txt"

            if utils.Client.is_file_present(output_txt_path) == True:
                delete_cmd = "rm -fr {}".format(output_txt_path)
                logger.info("Deleting existing output files")
                out = self.ssh_obj.execute(delete_cmd)

            cmd = "read_stripemap_entry --vsid {} -a {}".format(vsid, array_name)
            flag_rs_map, out_rs_map = self.run_cli_command(cmd, "wbt")
            if flag_rs_map == False or int(out_rs_map["data"]["returnCode"]) < 0:
                raise Exception(
                    "Command Execution failed; Please check and Retry again"
                )
            else:
                if utils.Client.is_file_present(output_txt_path) == False:
                    raise Exception("output file not generated")
                else:
                    logger.info("Output.txt file Generated!!!")
                    flag_wbt_par, map_dict_wbt_par = self.helper.wbt_parser(
                        output_txt_path
                    )
                    if flag_wbt_par == True:
                        logger.info("successfully parsed data from output.txt file")
                        return True, map_dict_wbt_par
                    else:
                        raise Exception("failed to parse data from output.txt file")
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            return False, None

    def wbt_translate_device_lba(
        self, array_name: str, logical_stripe_id: str = 0, logical_offset: str = 10
    ):
        """
        Method to translate device lba
        """
        try:
            output_txt_path = "/root/output.txt"
            if utils.Client.is_file_present(output_txt_path) == True:
                delete_cmd = "rm -fr {}".format(output_txt_path)
                logger.info("Deleting existing output files")

                out = self.ssh_obj.execute(delete_cmd)

            lba_cmd = "translate_device_lba --lsid {} --offset {} -v {}".format(
                logical_stripe_id, logical_offset, array_name
            )

            flag_lba, out_lba = self.run_cli_command(lba_cmd, "wbt")

            if flag_lba == False or int(out_lba["data"]["returnCode"]) < 0:
                raise Exception(
                    "Command Execution failed; Please check and Retry again"
                )
            else:
                if utils.Client.is_file_present(output_txt_path) == False:
                    raise Exception("output file not generated")
                else:
                    logger.info("Output.txt file Generated!!!")
                    flag_par_lba, trans_dict_lba = self.helper.wbt_parser(
                        output_txt_path
                    )
                    if flag_par_lba == True:
                        logger.info("Successfully data parsed from output.txt file ")
                        return True, trans_dict_lba
                    else:
                        raise Exception("failed to parse output.txt file")
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            return False, None

    def wbt_write_uncorrectable_lba(self, device_name: str, lba: str):
        """
        Method to write uncorrectable lba
        """
        try:
            cmd = "write_uncorrectable_lba --dev {} --lba {}  ".format(device_name, lba)
            out = self.run_cli_command(cmd, command_type="wbt")
            if out[0] == True:
                logger.info("Status_code={}".format(out[1]["status_code"]))
                if (
                    int(out[1]["data"]["returnCode"]) >= 0
                    and out[1]["description"].lower() == "pass"
                    and out[1]["status_code"] == 0
                ):
                    logger.info(
                        "Successfully injected error to the device {} in lba {}".format(
                            device_name, lba
                        )
                    )
                    return True, out
                else:
                    raise Exception(
                        "Failed to inject error to the device {} in lba {} ".format(
                            device_name, lba
                        )
                    )
        except Exception as e:
            logger.error("command execution failed because  of {}".format(e))
            return False, out

    def wbt_read_raw(self, dev: str, lba: str, count: str):
        """
        Method to read raw
        """
        try:
            file_name = "/tmp/{}.bin".format(self.helper.random_File_name())
            wbt_cmd = "read_raw --dev {} --lba {} --count {}  --output {} ".format(
                dev, lba, count, file_name
            )
            flag, out = self.run_cli_command(wbt_cmd, "wbt")
            if flag == True and int(out["data"]["returnCode"]) >= 0:
                logger.info(
                    "Successfully executed read_raw command on device  {} from lba {}".format(
                        dev, lba
                    )
                )
                return True, out
            else:
                logger.error(
                    "read_raw command execution failed with return code {} ".format(
                        out["data"]["returnCode"]
                    )
                )
                return False, None
        except Exception as e:
            logger.error("command execution failed because of  {}".format(e))
            return False, None

    def core_dump(self):
        """
        Method to collect core dump by giving different options depending on whether poseidonos is running
        """
        try:

            if self.helper.check_pos_exit() == False:
                dump_type = "triggercrash"
            else:
                dump_type = "crashed"

            command = "{}/tool/dump/trigger_core_dump.sh {}".format(
                self.pos_path, dump_type
            )
            out = self.ssh_obj.execute(command)
            logger.info("core dump file creation: {}".format(out))
            return out
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def updateeventwrr_devel(self, name: str, weight: str) -> (bool, dict):

        try:

            command = f"update-event-wrr --name {name} --weight {weight}"
            cli_error, jout = self.run_cli_command(command, "devel")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")

        except Exception as e:
            logger.error(e)
            return False, jout

    def reseteventwrr_devel(self) -> (bool, dict):

        try:

            command = "reset-event-wrr"
            cli_error, jout = self.run_cli_command(command, "devel")
            if cli_error == True:
                return True, jout
            else:
                raise Exception("CLI Error")

        except Exception as e:
            logger.error(e)
            return False, jout
