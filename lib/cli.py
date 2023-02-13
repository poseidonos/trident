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
import logger
import utils
import helper
import json
import pprint
from datetime import timedelta
from threading import Thread
from threading import Lock

logger = logger.get_logger(__name__)

class LinuxCLI:
    """
    This is a class to execute commands to linux Cli

    Attributes:
        con (object): Target ssh obj
    """

    def __init__(self, con: object) -> None:
        """   
        The constructor for for LinuxCli class

        Parameters:
            con (object): target ssh obj
        """
        self.ssh_obj = con

    def systemctl_servie(self, operation: str, service: str):
        """
        Method is to perform systemctl operation to linux service
           
        Parameters:
            operation (str): Service operation such as [start/stop]
            service (str): Name of the service

        Returns:
            A touple of Status and Comnad Response
        """
        try:
            cmd = f'systemctl {operation} {service}.service'
            out = self.ssh_obj.execute(cmd, get_pty=True)
            return True, out
        except Exception as e:
            logger.error(f"failed to {operation} {service} due to {e}")
            return False, out

    def pos_service_start(self):
        """ Method to start poseidonos service """
        return self.systemctl_servie("start", "poseidonos")

    def pos_service_stop(self):
        """ Method to stop poseidonos service """
        return self.systemctl_servie("stop", "poseidonos")

    def pos_service_status(self):
        """ Method to get status of poseidonos service """
        return self.systemctl_servie("status", "poseidonos")

    def pos_xpo_service_start(self):
        """ Method to start pos-exporter service """
        return self.systemctl_servie("start", "pos-exporter")

    def pos_xpo_service_stop(self):
        """ Method to stop pos-exporter service """
        return self.systemctl_servie("stop", "pos-exporter")

    def pos_xpo_service_status(self):
        """ Method to get status of pos-exporter service """
        return self.systemctl_servie("status", "pos-exporter")

    def kill_process(self, process: str, signal: int):
        """ 
        Method to kill process with selected signal

        Parameters:
            process (str) : Name of the process
            signal (int) : Signal number
        
        Returns:
            A touple of Status and Comnad Response
        """
        try:
            out = self.ssh_obj.execute(command=f"pkill {signal} {process}")
            return True, out
        except Exception as e:
            logger.error(f"POS kill {signal} failed due to {e}")
            return False, out

    def pos_kill(self, signal=-9):
        """ Method to kill pos with selected signal (defaul is -9) """
        return self.kill_process("poseidonos", signal=signal)

    def check_pos_pid(self) -> str:
        """ Method to check POS process """
        command = "ps -aef | grep -i poseidonos"
        out = self.ssh_obj.execute(command)
        ps_out = "".join(out)
        if "bin/poseidonos" not in ps_out:
            logger.info("POS IS NOT RUNNING")
            return True
        else:
            logger.warning("POS IS RUNNING")
            return False
        
    def check_pos_service(self) -> str:
        """ Method to check POS service status """
        cmd = 'systemctl is-active  poseidonos.service'
        out = self.ssh_obj.execute(cmd, get_pty=True)
        if "active" in out[0]:
            logger.info("POS IS RUNNING")
            return False
        else:
              logger.warning("POS IS NOT RUNNING")
              return True


class PosCLI:
    """
    The PosCli class execute commands to POS cli

    Attributes:
        con (object): target ssh obj
        data_dict (dict): pos_config details from testcase/config_files/`.json
        pos_source_path (str): pos souce code path
    """

    def __init__(self, con, data_dict: dict,
                 pos_cli_path: str = None) -> None:
        """
        The constructor for PosCli class

        Parameters:
            con (object): target ssh obj
            data_dict (dict): pos_config details from testcase/config_files/`.json
            pos_source_path (str): pos souce code path
        """

        self.ssh_obj = con
        self.data_dict = data_dict
        self.cli_path = pos_cli_path
        self.array_data = {}
        self.cli_history = []
        self.cmd_completion_time = 0
        self.lock = Lock()
       
    def run_cli_command(self, command: str, command_type: str = "request",
                        timeout: int = 0) -> (bool, dict()):
        """
        Method to Execute CLI commands and return Response

        Parameters::
            command (str):  cli command to be executed
            command_type (str) : Command type [array, device, system, qos, volume]
            timeout (int) : time in seconds to wait for compeltion |default 30 seconds as max time allowed time is 30 sec wait
        """

        try:
            retry_cnt = 1
            cmd = f"{self.cli_path} {command_type} {command} --json-res"

            if timeout > 0:
                cmd = f"{cmd} --timeout={timeout}"

            start_time = time.time()
            run_end_time = start_time + 120        # Wait for 2 minutes

            while time.time() < run_end_time:
                listout = self.ssh_obj.execute(cmd, get_pty=True)

                elapsed_time_secs = time.time() - start_time
                self.cmd_completion_time = timedelta(seconds=elapsed_time_secs)
                logger.debug(
                    f"Command execution completed in {elapsed_time_secs} secs")
                
                out = "".join(listout)
                if "volume mount" in cmd:
                    out = listout[1] if len(listout) > 1 else "".join(listout)

                if "cannot connect to the PoseidonOS server" in out:
                    logger.warning(
                        "POS is not running! Please start POS and try again!"
                    )
                    return False, out

                if "invalid data metric" in out:
                    logger.warning("Invalid syntax passed to the command ")
                    return False, out

                if "invalid json file" in out:
                    logger.error("Passed file contains invalid json data")
                    return False, out

                if "Receiving error" in out:
                    logger.error("POS crashed in between! please check POS logs")
                    return False, out

                err_msg = "PoseidonOS may be processing a command. Please try after a while."
                if err_msg in out:
                    retry_cnt += 1
                    time.sleep(5)
                    logger.warning(err_msg)
                    continue
                
                parse_out = self.parse_out(out, cmd)
                self.add_cli_history(parse_out)
                break

            if parse_out["status_code"] == 0:
                return True, parse_out
            else:
                return False, parse_out
        except Exception as e:
            logger.error(f"Command Execution failed because of {e}")
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

    def dump_cli_history(self, clean=True):
        """
        Method to dump cli command history for debugging
        """
        for cli in self.cli_history:
            logger.info(f"{cli}")

        if clean:
            logger.info("Deleting old cli history")
            self.cli_history = []

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

    ################################### System ################################
    def system_start(self, timeout: int = 0) -> (bool, dict()):
        """
        Method to start pos

        Parameters:
            timeout: Cli timeout 
        """
        try:
            cli_rsp, jout = self.run_cli_command("start", timeout=timeout,
                                                 command_type="system")
            if cli_rsp == False:
                raise Exception(f"CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"System start command failed due to {e}")
            return False, jout

    def system_stop(self, timeout: int = 300) -> (bool, dict()):
        """
        Method to stop poseidon

        Parameters:
            timeout (int) "timeout to wait POS map" (optional) | (default =300)
        """
        try:
            cli_rsp, jout = self.run_cli_command("stop --force", timeout=timeout,
                                                 command_type="system")
            if cli_rsp == False:
                raise Exception(f"CLI Error")
            
            if jout["output"]["Response"]["result"]["status"]["code"] != 0:
                logger.error("POS graceful shutdown failed.")
                return False, jout

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"System Stop command failed due to {e}")
            return False, jout

    def system_setproperty(self, rebuild_impact: str) -> (bool, dict()):
        """
        Method to set the rebuild impact

        Parameters:
            Rebuild_impact (str) : rebuild weight

        Returns:
            Tuple of (Comamnd Status, Comamnd Response) 
        """
        try:
            cmd = "set-property --rebuild-impact {}".format(rebuild_impact)
            cli_rsp, jout = self.run_cli_command(cmd, command_type="system")
            
            if cli_rsp == False:
                raise Exception(f"CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"System set property command failed due to {e}")
            return False, jout


    def system_info(self) -> (bool, dict()):
        """
        Method to get system info of pos

        Returns:
            Tuple of (Comamnd Status, Comamnd Response) 
        """
        try:
            cli_rsp, jout = self.run_cli_command("info", command_type="system")
            
            if cli_rsp == False:
                raise Exception(f"CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"System info command failed due to {e}")
            return False, jout

    ################################ Devel ###################################
    def devel_resetmbr(self) -> (bool, dict()):
        """
        Method to reset mbr

        Returns:
            Tuple of (Comamnd Status, Comamnd Response)
        """
        try:
            cli_rsp, jout = self.run_cli_command("resetmbr", command_type="devel")
            
            if cli_rsp == False:
                raise Exception(f"CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Devel resetmbr command failed due to {e}")
            return False, jout

    def devel_eventwrr_update(self, name: str, weight: str) -> (bool, dict):
        """
        Method to event writer update

        Parameters:
            name (str): Name of event
            weight (str): Weight of Event

        Returns:
            Tuple of (Comamnd Status, Comamnd Response)
        """
        try:

            command = f"update-event-wrr --name {name} --weight {weight}"
            cli_rsp, jout = self.run_cli_command(command, "devel")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Devel event writter update failed due to {e}")
            return False, jout

    def devel_eventwrr_reset(self) -> (bool, dict):
        """
        Method to event writer reset

        Returns:
            Tuple of (Comamnd Status, Comamnd Response)
        """
        try:
            command = "reset-event-wrr"
            cli_rsp, jout = self.run_cli_command(command, "devel")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Devel event writter reset failed due to {e}")
            return False, jout


    ################################ Array   #################################
    def array_list(self) -> (bool, dict()):
        """
        Method to list array
        """
        try:
            self.array_dict = {}
            cli_rsp, jout = self.run_cli_command("list", command_type="array")
            
            if cli_rsp == False:
                if (int(jout["status_code"]) == 1225
                    or int(jout["status_code"]) == 1226):
                    logger.info(jout["description"])
                    return True, jout
                else:
                    raise Exception(f"CLI Error")
                
            out = jout["output"]["Response"]
            if jout["data"] is None:
                logger.info("No arrays present in the config")
                return True, out
            else:
                for array in out["result"]["data"]["arrayList"]:
                    a_name = array["name"]
                    a_status = array["status"]
                    self.array_dict[a_name] = a_status

                num_array = len(list(self.array_dict.keys()))
                array_list = list(self.array_dict.keys())
                logger.info(f"{num_array} Arrays are present. {array_list}")

            return True, out
        except Exception as e:
            logger.error(f"Array list command failed due to {e}".format(e))
            return False, jout

    def array_create(self, array_name: str, write_buffer: str,
                     data: list, spare: list = [],
                     raid_type: str = None) -> (bool, dict()):
        """
        Method to create array
        
        Parameters:
            array_name (str): Name of the array
            write_buffer (str): Name of the uram
            data (list): List of the data devices
            spare (list): List of the spare devices
            raid_type (str): Raid type
            array_name (str): name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            data_disks = ",".join(data)
            cmd = f"create -b {write_buffer} -d {data_disks} -a {array_name}"

            if len(spare) > 0:
                spare_disks = ",".join(spare)
                cmd = f"{cmd} -s {spare_disks}"

            if raid_type.lower() == "no-raid" or raid_type.lower() == "noraid":
               cmd = f"{cmd} --no-raid"
            else:
                cmd = f"{cmd} --raid {raid_type}"

            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array create command failed due to {e}")
            return False, jout

    def array_autocreate(self, array_name: str, buffer_name: str, 
                         num_data: int, raid: str = None,
                         num_spare: int = 0) -> (bool, dict()):
        """
        Method to ameutocreate array

        Parameters:
            array_name (str): Name of the array
            num_data (str): Number of data devices
            num_spare (str): Number of spare | 0 if no spare
            raid (str): Type of raid

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"autocreate -a {array_name} -b {buffer_name} -d {num_data}"

            if num_spare > 0:
                cmd = f"{cmd} -s {num_spare}"

            if raid.lower() == "no-raid" or raid.lower() == "noraid":
               cmd = f"{cmd} --no-raid"
            else:
                cmd = f"{cmd} --raid {raid}"

            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array auto create command failed due to {e}")
            return False, jout

    def array_mount(self, array_name: str, 
                    write_back: bool = False) -> (bool, dict()):
        """
        Method to mount array

        Parameters:
            array_name (str): Name of the array
            write_back (bool): Mount array in Write Through if True else Write Back

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"mount -a {array_name}"
            if write_back == False:
                cmd += " --enable-write-through"

            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array mount comand failed due to {e}")
            return False, jout

    def array_unmount(self, array_name: str) -> (bool, dict()):
        """
        Method to unmount array

        Parameters:
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"unmount -a {array_name} --force"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array unmount command failed due to {e}")
            return False, jout

    def array_delete(self, array_name: str = None) -> (bool, dict()):
        """
        Method to delete array

        Parameters:
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"delete -a {array_name} --force"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array delete command failed due to {e}")
            return False, jout

    def array_info(self, array_name: str) -> (bool, dict()):
        """
        Method to get array information

        Parameters:
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        spare_dev = []
        data_dev = []
        buffer_dev = []
        try:
            cmd = f"list -a {array_name}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")

            if cli_rsp == False:
                raise Exception("CLI Error")

            if jout["output"]["Response"]["result"]["status"]["code"] == 0:
                array_exist = True
            else:
                array_exist = False

            if array_exist:
                array_data = jout["data"]
                array_state = array_data["state"]
                array_size = array_data["capacity"]
                array_situation = array_data["situation"]
                rebuild_progress = array_data["rebuildingProgress"]
                uniqueId = array_data['uniqueId']
                for dev in array_data["devicelist"]:
                    if dev["type"] == "DATA":
                        data_dev.append(dev["name"])
                    elif dev["type"] == "SPARE":
                        spare_dev.append(dev["name"])
                    elif dev["type"] == "BUFFER":
                        buffer_dev.append(dev["name"])
                    else:
                        logger.error("Disk type is unknown")
                                    
                self.normal_data_disks = list(
                        [dev for dev in data_dev if "REMOVED" not in dev])
                self.array_data[array_name] = {
                    "state": array_state,
                    "size": array_size,
                    "situation": array_situation,
                    "rebuilding_progress": rebuild_progress,
                    "data_list": data_dev,
                    "spare_list": spare_dev,
                    "buffer_list": buffer_dev,
                    'uniqueId' :uniqueId
                }
            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array info command failed due to {e}")
            return False, jout

    def array_addspare(self, 
                       device_name: str, array_name: str) -> (bool, dict()):
        """
        Method to add spare drive

        Parameters:
            device_name (str): Name of the device
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"addspare -s {device_name} -a {array_name}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array addspare command failed due to {e}")
            return False, jout

    def array_rmspare(self, 
                      device_name: str, array_name: str) -> (bool, dict()):
        """
        Method to remove spare drive

        Parameters:
            device_name (str): Name of the device
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"rmspare -s {device_name} -a {array_name}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array remove spare command failed due to {e}")
            return False, jout

    def array_replace_disk(self, device_name: str,
                           array_name: str) -> (bool, dict()):
        """
        Method to replace data drive with spare drive

        Parameters:
            device_name (str): Name of the device
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"replace -d {device_name} -a {array_name}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array replace disk command failed due to {e}")
            return False, jout

    def array_rebuild(self, array_name: str) -> (bool, dict()):
        """
        Method to start the array rebuild

        Parameters:
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cmd = f"rebuild -a {array_name}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="array")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Array rebuild command failed due to {e}")
            return False, jout

    ################################## Device ################################
    def device_scan(self) -> (bool, dict()):
        """
        Method to scan devices

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            cli_rsp, jout = self.run_cli_command("scan", command_type="device")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Device scan command failed due to {e}")
            return False, jout

    def device_create(self, uram_name: str, bufer_size: str = None,
                      strip_size: str = None, numa: int = 0) -> (bool, dict()):
        """
        Method to create malloc device

        Parameters:
            uram_name (str): Name of buffer device
            buffer_szie (str): Buffer device size
            strip_size (str): Size of the stripe
            numa (int): Numa node number

        Returns:
            Tuple of (Status, Comamnd Response) 
        """
        try:
            for uram in self.data_dict["device"]["uram"]:
                if uram["uram_name"] == uram_name:
                    bufer_size = bufer_size or uram["bufer_size"]
                    strip_size = strip_size or uram["strip_size"]
                    numa = numa or uram["numa_node"]
                    break

            cmd = f'create --device-name {uram_name} --num-blocks {bufer_size}'
            cmd = f'{cmd} --block-size {strip_size} --numa {numa} --device-type "uram"'

            cli_rsp, jout = self.run_cli_command(cmd, command_type="device")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error("Device create command failed due to {}".format(e))
            return False, jout

    def device_list(self) -> (bool, dict()):
        """
        Method to list devices

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cli_rsp, jout = self.run_cli_command("list", command_type="device")

            if cli_rsp == False:
                raise Exception("CLI Error")

            devices = []
            self.device_map = {}
            self.device_type = {}
            self.dev_type = {"NVRAM": [], "SSD": []}

            if jout["description"].lower() == "no any device exists":
                logger.info("No devices listed")
                return True, jout

            if "data" in jout:
                dev = jout["data"]["devicelist"]
                for device in dev:
                    devices.append(device["name"])
                    if device["type"] == "NVRAM":
                        dev_map = {
                            "name": device["name"],
                            "addr": device["name"],
                            "mn": device["modelNumber"],
                            "sn": device["serialNumber"],
                            "size": device["size"],
                            "type": device["type"],
                            "class": device["class"],
                            "numa": device["numa"],
                        }
                    else:
                        dev_map = {
                            "name": device["name"],
                            "addr": device["address"],
                            "mn": device["modelNumber"],
                            "sn": device["serialNumber"],
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

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Device list command failed due to {e}")
            return False, None, None, None, None

    def device_smart(self, devicename: str) -> (bool, dict()):
        """
        Method to get smart details of a devce

        Parameters:
            device_name : Name of the device

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "smart -d {}".format(devicename)
            cli_rsp, jout = self.run_cli_command(cmd, command_type="device")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Device smart command failed due to {e}")
            return False, jout

    def device_smart_log(self, devicename: str) -> (bool, dict()):
        """
        Method to get smart details of a devce

        Parameters:
            device_name : Name of the device

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            self.smart_log_dict = {}
            cmd = "smart-log -d {}".format(devicename)
            cli_rsp, jout = self.run_cli_command(cmd, command_type="device")
            if cli_rsp == False:
                raise Exception("CLI Error")
            self.smart_log_dict[devicename] = jout['data']

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Device smart log command failed due to {e}")
            return False, jout

    ################################### Logger ###############################
    def logger_set_log_level(self, level: str) -> (bool, dict()):
        """
        Method to set the log level

        Parameters:
            device_name : Name of the device

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "set-level --level {}".format(level)
            cli_rsp, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Logger set level command failed due to {e}")
            return False, jout

    def logger_get_log_level(self) -> (bool, dict()):
        """
        Method to get the log level

        Parameters:
            device_name : Name of the device

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "get-level"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Logger get level command failed due to {e}")
            return False, jout

    def logger_apply_log_filter(self) -> (bool, dict()):
        """
        Method to set log filter

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "apply-filter"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Logger apply filter command failed due to {e}")
            return False, jout

    def logger_info(self) -> (bool, dict()):
        """
        Method to get logger info

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "info"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Logger info command failed due to {e}")
            return False, jout

    ################################### Telemetry ############################

    def telemetry_start(self) -> (bool, dict()):
        """
        Method to start telemetry

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "start"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Telemetry start command failed due to {e}")
            return False, jout

    def telemetry_stop(self) -> (bool, dict()):
        """
        Method to stop telemetry

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "stop"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Telemetry stop command failed due to {e}")
            return False, jout

    def telemetry_get_property(self) -> (bool, dict()):
        """
        Method to get telemetry property

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "get-property"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Telemetry get-property command failed due to {e}")
            return False, jout

    def telemetry_set_property(self, publication_list_path='/etc/pos/pos-prometheus.yml') -> (bool, dict()):
        """
        Method to set telemetry property

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = f"set-property --publication-list-path {publication_list_path}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Telemetry set property command failed due to {e}")
            return False, jout

    ################################### QOS ##################################
    def qos_create_volume_policy(self, volumename: str, arrayname: str,
                                 maxiops: str, maxbw: str, miniops: str = None,
                                 minbw: str = None) -> (bool, dict()):
        """
        Method to create qos volume policy

        Parameters:
            volumename (str): Name of the volume
            arrayname (str): Name of the array
            maxiops (str): Maximum QOS values of IOPs
            maxbw (str): Maximum QOS values of Bandwidth
            miniops (str): Minumum QOS values of IOPS
            minbw (str): Minimum QOS values of Bandwidth

        Returns:
            Tuple of (Status, Comamnd Response)
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

            cli_rsp, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"QOS create volume policy command failed due to {e}")
            return False, jout

    def qos_reset_volume_policy(self, volumename: str, 
                                arrayname: str) -> (bool, dict()):
        """
        Method to reset volume policy

        Parameters::
            volumename (str): Name of the volume
            arrayname (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "reset -v {} -a {}".format(volumename, arrayname)
            cli_rsp, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"QOS reset volume policy command failed due to {e}")
            return False, jout

    def qos_list_volume_policy(self, volumename: str,
                              arrayname: str) -> (bool, dict()):
        """
        Method to list volume policy

        Parameters:
            volumename (str) : Name of the volume
            arrayname (str) : Name of the array

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = "list -v {} -a {}".format(volumename, arrayname)
            cli_rsp, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"QOS list volume policy command failed due to {e}")
            return False, jout

    ################################### Volume ###############################
    def volume_list(self, array_name: str) -> (bool, dict()):
        """
        Method to list volumes

        Parameters:
            array_name (str): Name of the array

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            self.vol_dict = {}
            cmd = f"list -a {array_name}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")

            if cli_rsp == False:
                raise Exception("CLI Error")

            if jout["status_code"] != 0:
                raise Exception(out["description"])

            no_vols_str = f"no any volume exist in {array_name}"
            if no_vols_str == jout["description"]:
                logger.warning(jout["description"])
                self.vols = []
                return True, jout

            for vol in jout["data"]["volumes"]:
                self.vol_dict[vol["name"]] = {
                    "index": vol["index"],
                    "total": vol["total"],
                    "status": vol["status"],
                    "max_iops": vol["maxiops"],
                    "maxbw": vol["maxbw"],
                }
            self.vols = list(self.vol_dict.keys())
            return True, jout
        except Exception as e:
            logger.error(f"Volume list command failed due to {e}")
            return False, jout

    def volume_info(self, array_name: str,
                    vol_name: str) -> (bool, dict()):
        """
        Method to get volume information

        Parameters:
            array_name (str): Name of the array
            array_name (str): Name of the volume

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            self.volume_data = {}
            self.volume_data[array_name] = {}

            cmd = f"list -a {array_name} -v {vol_name}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")

            if cli_rsp == False:
                raise Exception("CLI Error")

            if jout["output"]["Response"]["result"]["status"]["code"] == 0:
                vol_data = jout["data"]
                self.volume_data[array_name][vol_name] = {
                    "uuid": vol_data["uuid"],
                    "name": vol_data["name"],
                    "total_capacity": vol_data["total"],
                    "status": vol_data["status"],
                    "max_iops": vol_data["maxiops"],
                    "min_iops": vol_data["miniops"],
                    "max_bw": vol_data["maxbw"],
                    "min_bw": vol_data["minbw"],
                    "subnqn": vol_data["subnqn"],
                    "array_name": vol_data["array_name"],
                }
                vol_status = self.volume_data[array_name][vol_name]["status"]
                if vol_status == "Mounted":
                    cap = vol_data["remain"]
                    self.volume_data[array_name][vol_name]["remain"] = cap
            else:
                logger.error("Failed to execute volume info command")
                return False, jout

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Volume info command failed due to {e}")
            return False, jout

    def volume_create(self, volumename: str, size: str, array_name: str,
                      iops: str = 0, bw: str = 0) -> (bool, dict()):
        """
        Method to create volume
        Parameters:
            volumename (str): Name of the volume
            size (str): Size of the volume
            array_name (str): Name of the array
            iops (str): Maximum QOS values of IOPS
            bw (str): Maximum QOS values of Bandwidth
            #TODO add max and min iops

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = f"create -a {array_name} -v {volumename} --size {size}"
            cmd = f"{cmd} --maxiops {iops} --maxbw {bw}"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Volume create command failed due to {e}")
            return False, jout

    def volume_delete(self, volumename: str, array_name: str) -> (bool, dict()):
        """
        Method to delete volume
        Parameters:
            volumename (str) : Name of the volume
            array_name (str) : Name of the array

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = f"delete -a {array_name} -v {volumename} --force"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Volume delete command failed due to {e}")
            return False, jout

    def volume_mount(self, volumename: str,
                     array_name: str, nqn: str = None) -> (bool, dict()):
        """
        Method to mount volume
        Parameters:
            volumename (str): Name of the volume
            array_name (str) Name of the array
            nqn (str) : Subsystem name  |if nqn == None then random NQN will be selected by POS

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = f"mount -v {volumename} -a {array_name} --force"
            if nqn:
                cmd += " --subnqn {}".format(nqn)
            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")

            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Volume mount command failed due to {e}")
            return False, jout

    def volume_rename(self, new_volname: str,
                      volname: str, array_name: str) -> (bool, dict()):
        """
        Method to rename volume

        Parameters:
            new_volname (str): Name of new volume
            volname (str): Name of old volume
            array_name (str): Name of array


        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = f"rename -v {volname} -a {array_name} -n {new_volname}"

            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Volume rename command failed due to {e}")
            return False, jout

    def volume_unmount(self,
                       volumename: str, array_name: str) -> (bool, dict()):
        """
        Method to unmount volume

        Parameters:
            volumename (str): Name of the volume
            array_name (str): Name of array

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = f"unmount -v {volumename} -a {array_name} --force"
            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Volume unmount command failed due to {e}")
            return False, jout

    def volume_mount_with_subsystem(self, volumename: str, nqn_name: str,
                                    ip: str, vcid: str, array_name: str
                                    ) -> (bool, dict()):
        """
        Method to mount volume with subsystem

        Parameters::
            volumename (str): Name of the volume
            nqn_name (str): Name of the SS
            array_name (str): Name of the array
            ip (str) : IP details
            vcid (str) : Port details

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            cmd = f"mount-with-subsystem -v {volumename} --subnqn {nqn_name}"
            cmd = f"{cmd} -a {array_name} --trtype tcp --traddr {ip} --trsvcid {vcid} --force"

            cli_rsp, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Volume mount with subsystem command failed due to {e}")
            return False, jout

    ################################## Subsystem #############################
    def subsystem_create(self, nqn_name: str, ns_count: str = None,
                         serial_number: str = None, model_name: str = None,
                         ) -> (bool, dict()):
        """
        Method to create nvmf subsystem
        Parameters::
            nqn_name (str) : Name of subsystem
            ns_count (int) : Max namespace supported by subsystem
            serial_number (str) : Serial number of subsystem
            model_name (str) : Model number of subsystem
        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            subsystem = self.data_dict["subsystem"]["pos_subsystems"]
            ns_count = ns_count or subsystem[0]["ns_count"]
            serial_number = serial_number or subsystem[0]["serial_number"]
            model_name = model_name or subsystem[0]["model_name"]

            cmd = "create --subnqn {} --serial-number {} --model-number {} \
                    --max-namespaces {} --allow-any-host".format(
                nqn_name, serial_number, model_name, ns_count
            )
            cli_rsp, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Subsystem create command failed due to {e}")
            return False, jout

    def subsystem_list(self) -> (bool, dict()):
        """
        method executes nvmf_get_subsystems

        Returns:
            Tuple of (Status, Comamnd Response)
        """
        try:
            self.nvmf_subsystem, temp = {}, {}
            cli_rsp, jout = self.run_cli_command("list", 
                                                 command_type="subsystem")
            if cli_rsp == False:
                raise Exception("CLI Error")

            for data in jout["data"]["subsystemlist"]:
                temp = data
                self.nvmf_subsystem[data["nqn"]] = temp

            logger.info(f"Subsystem list {self.nvmf_subsystem}")
            #return (True, self.nvmf_out)

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Subsystem list command failed due to {e}")
            return False, jout

    def subsystem_add_listner(self, nqn_name: str, mellanox_interface: str,
                         port: str, transport: str = "TCP") -> (bool, dict()):
        """
        Method to add nvmf listner
        Parameters:
            nqn_name (str) : Subsystem name
            mellanox_interface
        """
        try:

            cmd = f"add-listener --subnqn {nqn_name} --trtype {transport}"
            cmd = f"{cmd} --traddr {mellanox_interface} --trsvcid {port}"

            cli_rsp, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Subsystem add listner command failed due to {e}")
            return False, jout

    def subsystem_create_transport(self, buf_cache_size: str = 64,
                                   num_shared_buf: str = 4096,
                                   transport_type: str = "TCP"
                                   ) -> (bool, dict()):
        """
        Method to create transport

        Parameters:
            buf_cache_size (str) : Buffer size for TCP packets
            num_share_buf (str) : Num of buffers
            transport type (str) : Transport Type. TCP/RDMA
        """
        try:
            ttype = transport_type.upper()
            cmd = f"create-transport --buf-cache-size {buf_cache_size}"
            cmd = f"{cmd} --trtype {ttype} --num-shared-buf {num_shared_buf}"

            cli_rsp, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Subsystem create transport cmd failed due to {e}")
            return False, jout

    def subsystem_delete(self, nqn_name: str, force: bool = True) -> (bool, dict()):
        """method to delete subsystem
        Parameters::
            nqn_name (str) name of the subsystem
            force (bool) |default True

        """
        try:
            force = " --force" if force else " "
            cmd = f"delete --subnqn {nqn_name} {force}"
            cli_rsp, jout = self.run_cli_command(cmd, "subsystem")
            if cli_rsp == False:
                raise Exception("CLI Error")

            return cli_rsp, jout
        except Exception as e:
            logger.error(f"Subsystem dlete command failed due to {e}")
            return False, jout

    # TODO check if the below Methods are to be open sourced/ renamed for open sourcing
    ######################################wbt#######################################

    def wbt_do_gc(self, array_name: str):
        """
        Method to do gc
        """
        try:
            cmd = "do_gc --array {}".format(array_name)
            cli_rsp, jout = self.run_cli_command(cmd, "wbt")
            if cli_rsp == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_get_gc_status(self, array_name: str):
        """
        Method to get gc status
        """
        try:
            cmd = "get_gc_status --array {}".format(array_name)
            cli_rsp, jout = self.run_cli_command(cmd, "wbt")
            if cli_rsp == True:
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
        self, array_name: str, normal: int, urgent: int
    ):
        """
        Method to set gc threshold value to the given array
        """
        try:
            cmd = "set_gc_threshold --array {} --normal {} --urgent {}".format(
                array_name, normal, urgent
            )
            cli_rsp, jout = self.run_cli_command(cmd, "wbt")
            if cli_rsp == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_get_gc_threshold(self, array_name: str):
        """
        Method to get gc threshold
        """
        try:
            cmd = "get_gc_threshold --array {}".format(array_name)
            cli_rsp, jout = self.run_cli_command(cmd, "wbt")
            if cli_rsp == True:
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

    def wbt_flush(self, array_name: str):
        """
        Method to flush
        """
        try:
            cmd = "flush -a {}".format(array_name)
            cli_rsp, jout = self.run_cli_command(cmd, "wbt")
            if cli_rsp == True:
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_read_vsamap_entry(
        self, volumename: str, rba: str, array_name: str
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
            cli_rsp, jout = self.run_cli_command(vsamap_entry_cmd, "wbt")
            if cli_rsp == True:
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

    def wbt_read_stripemap_entry(self, vsid: str, array_name: str):
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



class Cli(LinuxCLI, PosCLI):

    """
    The PosCli class execute commands to POS cli

    Attributes:
        con (object): target ssh obj
        data_dict (dict): pos_config details from testcase/config_files/`.json
        pos_source_path (str): pos souce code path
    """

    def __init__(self, con, data_dict: dict,
                pos_as_service: bool = False,
                pos_source_path: str = None) -> None:
        """
        The constructor for Cli class

        Parameters:
            con (object): Target ssh obj
            data_dict (dict): pos_config details from testcase/config_files/`.json
            pos_source_path (str): pos souce code path
        """

        self.ssh_obj = con
        self.helper = helper.Helper(con, pos_as_service=pos_as_service)
        self.pos_as_service = pos_as_service

        if not self.pos_as_service:
            self.cli_path =  f'{pos_source_path}/bin/poseidonos-cli'
        else:
            self.cli_path = "poseidonos-cli"

        # Initialize Base Classes
        LinuxCLI.__init__(self, con)
        PosCLI.__init__(self, con, data_dict, self.cli_path)

        # Temp POS Info Storage 
        self.array_data = {}
        self.cli_history = []

        self.lock = Lock()

    def pos_start(self, timeout=120, verify=True):
        """
        Method to start pos

        Parameters:
            timeout (int): POS start timeout or wait time
        """
        try:
            if self.pos_as_service:   # POS as service
                res, jout = self.pos_service_start()
            else:
                res, jout = self.system_start()

            if res and verify:
                start_time = time.time()
                run_end_time = start_time + timeout

                success = False
                while time.time() < run_end_time:
                    if self.helper.check_pos_exit() == True:
                        logger.warning("Waiting for POS to be UP and running")
                        time.sleep(10) # Sleep 10 second
                        continue
                    success = True
                    break

                if not success:
                    raise Exception("POS is not listed after given timeout")
   
            return res, jout
        except Exception as e:
            logger.error(f"POS start failed due to {e}")
            return False, jout

    def pos_stop(self, grace_shutdown: bool = True,
                 timeout: int = 300, verify=True) -> (bool, dict()):
        """
        Method to stop poseidon

        Parameters:
            grace_shutdown (bool) : Stop pos gracefully after array unmount
            timeout (int): POS stop timeout or wait time
        """
        try:
            if grace_shutdown:
                assert self.array_list()[0] == True
                array_list = list(self.array_dict.keys())
                for array in array_list:
                    if self.array_dict[array].lower() == "mounted":
                        assert self.array_unmount(array_name=array)[0] == True

                if self.pos_as_service:
                    res, jout = self.pos_service_stop()
                else:
                    res, jout = self.system_stop(timeout=timeout)
            else:
                res, jout = self.pos_kill()

            if res == False:
                logger.error("POS stop failed")

            if res and verify:
                logger.info("POS shutdown successful. Verifying PID...")

                start_time = time.time()
                run_end_time = start_time + timeout

                success = False
                while time.time() < run_end_time:
                    if self.helper.check_pos_exit() == False:
                        logger.warning("POS is still active. Wait for 10 seconds...")
                        time.sleep(10) # Sleep 10 second
                        continue
                    success = True
                    break

                if not success:
                    raise Exception("POS process is listed after timeout")
             
            return res, jout
        except Exception as e:
            logger.error(f"POS stop failed due to {e}")
            return False, jout

    def check_pos_exit(self) -> bool:
        """ 
        Method to check pos running status

        Returns:
            Bool: True if pos is not running else False
        """
        if self.pos_as_service:
            return self.check_pos_service()
        else:
            return self.check_pos_pid()
 
