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
from datetime import timedelta
from threading import Thread
import logger
import utils
import helper


logger = logger.get_logger(__name__)


class Cli:
    """
    The Cli class contains objects for  POS cli
    Args:
        con (object) : target ssh obj
        pos_path (str) : path of the pos Source
        array_name (str) : name of the POS array
    """

    def __init__(
        self,
        con,
        pos_path,
        array_name="POS_ARRAY1",
    ):

        self.ssh_obj = con
        self.helper = helper.Helper(con)

        self.pos_path = pos_path
        self.array_name = array_name
        self.new_cli_path = "/bin/poseidonos-cli"  ##path of POS cli
        self.array_info = {}

    def run_cli_command(self, command, command_type="request", timeout=1800):
        """
        Method to Execute CLIT commands and return Response
        Args:
            command (str):  cli command to be executed
            command_type (str) : Command type [array, device, system, qos, volume]
            timeout (int) : time in seconds to wait for compeltion
        Returns:
            bool, list
        """

        try:
            retry_cnt = 1
            cmd = "{}{} {} {} --json-res".format(
                self.pos_path, self.new_cli_path, command_type, command
            )
            start_time = time.time()
            run_end_time = start_time + timeout
            while time.time() < run_end_time:
                out = self.ssh_obj.execute(cmd, get_pty=True)

                elapsed_time_secs = time.time() - start_time
                logger.info(
                    "command execution completed in  : {} secs ".format(
                        timedelta(seconds=elapsed_time_secs)
                    )
                )
                out = "".join(out)
                logger.info("Raw output of the command {} is {}".format(command, out))
                if "cannot connect to the PoseidonOS server" in out:
                    logger.warning(
                        "POS is not running! please start POS and try again!"
                    )
                    return False, out
                elif "invalid data metric" in out:
                    logger.warning("invalid syntax passed to the command ")
                    return False, out
                elif "invalid json file" in out:
                    logger.error("passed file contains invalid json data")
                    return False, out
                elif "Receiving error" in out:
                    logger.error("ibof os crashed in between ! please check ibof logs")
                    return False, out
                else:
                    if "volume mount" in cmd:
                        return (
                            True,
                            out,
                        )  ##################temp fix .. invalid json obtained for mount volume
                    parse_out = self.helper.parse_out(out, cmd)
                    assert self.helper.add_cli_history(parse_out=parse_out) == True

                    if parse_out["status_code"] == 0:
                        return True, parse_out
                    elif parse_out["status_code"] == 1030:
                        logger.info(
                            "Poseidonos is in Busy state, status code is {}. Command retry count is {}".format(
                                parse_out["status_code"], retry_cnt
                            )
                        )
                        retry_cnt += 1
                        time.sleep(5)
                        continue
                    else:
                        return False, out

        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False, None

    def get_pos_logs(self):

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
    def start_system(self):
        """
        Method to start pos
        Returns:
            bool, list
        """
        try:

            cli_error, jout = self.run_cli_command("start", "system")
            jout = []
            if cli_error == True:
                # un-commenting the code with tail script/pos.log
                """
                self.start_out = self.ssh_obj.run_async(f"tail -f {self.pos_path}/script/pos.log")
                thread = Thread(target=self.get_pos_logs, args =())
                thread.daemon = True
                thread.start()
                if self.start_out.is_complete() is False():
                """
                return True, jout
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def stop_system(
        self,
        grace_shutdown = True,
        time_out = 300,
    ) :
        """
        Method to stop poseidon
        Args:
            grace_shutdown (bool) :"flag to kill POS grace_fully" (optional) | (default= True),
            time_out (int) "timeout to wait POS map" (optional) | (default =300)
        Returns:
            bool, list
        """
        try:
            if grace_shutdown:
                assert self.list_array()[0] == True
                array_list = list(self.array_dict.keys())
                if len(array_list) == 0:
                    logger.info("No array found in the config")
                else:
                    for array in array_list:
                        assert self.info_array(array_name=array)[0] == True
                        if self.array_info[array]["state"].lower() == "mounted":
                            assert self.unmount_array(array_name=array)[0] == True
                        assert self.delete_array(array_name=array)[0] == True

                out = self.run_cli_command("stop --force", command_type="system")

                if out[0] == True:
                    if out[1]["output"]["Response"]["result"]["status"]["code"] == 0:
                        logger.info("POS was stopped successfully!!! verifying PID")
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
                                raise Exception("failed to kill pos")
            else:
                self.ssh_obj.execute(command="pkill -9 pos")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False
        return True

    def setposproperty_system(self, rebuild_impact: str):
        """
        method to set the rebuild impact
        Args:
            Rebuild_impact (str) : rebuild weight
        Returns:
            bool, list()
        """
        try:
            cmd = "set-property --rebuild-impact {}".format(rebuild_impact)
            cli_error, jout = self.run_cli_command(cmd, command_type="system")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def info_system(self):
        """
        method to get system info of pos
        Returns:
            bool, out
        """
        try:
            cmd = "info"
            cli_error, jout = self.run_cli_command(cmd, command_type="system")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ################################################array#######################################
    def list_array(self):
        """
        Method to list array
        Returns:
            bool, list(), dict()
        """
        try:
            self.array_dict = {}
            cmd = "list"
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                out = jout["output"]["Response"]
                if "There is no array" in out["result"]["data"]["arrayList"]:
                    logger.info("No arrays present in the config")
                    return True, out, self.array_dict
                else:
                    logger.info(out["result"]["data"]["arrayList"])
                    for i in out["result"]["data"]["arrayList"]:
                        a_name = i["name"]
                        a_status = i["status"]
                        self.array_dict[a_name] = a_status

                    return True, out, self.array_dict
            else:
                raise Exception("list array command execution failed ")
        except Exception as e:
            logger.error("list array command failed with exception {}".format(e))
            return False, out

    def create_array(
        self,
        write_buffer = "uram0",
        data = ["unvme-ns-0", "unvme-ns-1", "unvme-ns-2"],
        spare= ["unvme-ns-3"],
        raid_type= "RAID5",
        array_name = None,
    ) :
        """
        Method to create array
        Args:
            write_buffer (str) :name of the uram 
            data (list) : list of the data devices
            spare (list) : list of the spare devices
            raid_type (str) : Raid type
            array_name (str) : name of the array
        Returns:
            bool, list
        """
        try:
            data = ",".join(data)

            if array_name != None:
                self.array_name = array_name

            cmd = "create -b {} -d {} -a {} --raid {}".format(
                write_buffer, data, self.array_name, raid_type
            )
            if spare:
                spare = spare[0] if len(spare) == 0 else ",".join(spare)
                cmd += f" --spare {spare}"
            if raid_type == "no-raid":
                cmd.replace("raid RAID5", "--no-raid")

            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def mount_array(self, array_name: str = None, write_back=False):
        """
        Method to mount array
        Args:
            array_name (str) : name of the array
            write_back (bool)  : write through if True else write back
        Returns:   
            bool, list
           
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "mount -a {}".format(self.array_name)
            if write_back:
                cmd += "--enable-write-through"
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def unmount_array(self, array_name: str = None) :
        """
        Method to unmount array
        Args:
            array_name (str) : name of the array
        Returns:
            bool, list
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "unmount -a {} --force".format(self.array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def reset_devel(self) :
        """
        Method to array reset
        Returns:
            bool, list
        """
        try:
            cmd = "resetmbr"
            cli_error, jout = self.run_cli_command(cmd, command_type="devel")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to  {}".format(e))
            return False, jout

    def delete_array(self, array_name=None) :
        """
        Method to delete array
        Args:
            array_name (str) name of the array
        Returns:
            bool, list
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "delete -a {} --force".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def info_array(self, array_name = None) :
        """
        Method to get array information
        Args:
            array_name (str) name of the array
        Returns:
            (bool, list, list, str) 
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
                logger.error("list array device command execution failed")
                return False, out[1]
            if flag == True:
                array_state = out[1]["data"]["state"]
                array_situation = out[1]["data"]["situation"]
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
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False, None, None, None
        self.array_info[array_name] = {
            "state": array_state,
            "situation": array_situation,
            "data_list": data_dev,
            "spare_list": spare_dev,
            "buffer_list": buffer_dev,
        }
        return (
            True,
            out[1]["data"],
            array_state,
            array_situation,
            data_dev,
            spare_dev,
            buffer_dev,
        )

    def addspare_array(self, device_name, array_name = None):
        """
        Method to add spare drive
        Args:
            device_name (str) : name of the device
            array_name (str) : name of the array
        """
        try:
            cmd = "addspare -s {} -a {}".format(device_name, array_name)
            cli_error, out = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                status_code = out["status_code"]
                if status_code == 0:

                    return True, out
                else:
                    raise Exception(out["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, out

    def rmspare_array(self, device_name, array_name = None) :
        """
        Method to remove spare drive
        Args:
            device_name (str) : name of the device
            array_name (str) : name of the array
        Returns:
            bool, list
        """
        try:
            cmd = "rmspare -s {} -a {}".format(device_name, array_name)
            cli_error, out = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                status_code = out["status_code"]
                if status_code == 0:
                    return True, out
                else:
                    raise Exception(out["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, out

    def autocreate_array(
        self,
        array_name,
        buffer_name,
        num_data,
        num_spare,
        raid
    ) :
        """
        Method to ameutocreate array
        Args:
            array_name (str) : name of the array
            buffer_name (str) : name of the buffer
            num_data (str) : num of data devices
            num_spare (str) : num of spare | 0 if no spare
            raid (str) : type of raid
        Returns:
            bool, list
        """
        try:
            cmd = "autocreate --array-name {} --buffer {} --num-data-devs {} --num-spare {} --raid {}".format(
                array_name, buffer_name, num_data, num_spare, raid
            )

            cli_error, out = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                status_code = out["status_code"]
                if status_code == 0:
                    logger.info(out["description"])
                    return True, out
                else:
                    raise Exception(out["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, out

    ########################################################device######################
    def scan_device(
        self,
    ):
        """
        Method to scan devices
        Returns:
            bool, list
        """
        try:
            cmd = "scan"
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def create_device(
        self,
        uram_name = "uram0",
        bufer_size = "8388608",
        strip_size= "512",
        numa = "1",
    ) :
        """
        Method to create malloc device
        Args:
            uram_name (str) : name of uram
            buffer_szie (str) : |default 8GB
            strip_size (str) : 512
            num (str) : 1
        Returns:
            bool, list
        """
        try:
            cmd = 'create --device-name {} --num-blocks {} --block-size {} --device-type "uram" --numa {}'.format(
                uram_name, bufer_size, strip_size, numa
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def list_device(self) :
        """
        Method to list devices
        Returns:
            bool, dict()
        """
        try:
            cmd = "list"
            cli_error, out = self.run_cli_command(cmd, command_type="device")
            devices = []
            device_map = {}
            self.device_type = {}
            self.dev_type = {"NVRAM": [], "SSD": []}

            if cli_error == True:
                if out["status_code"] == 0:
                    if out["description"].lower() == "no any device exists":
                        logger.info("No devices listed")
                        return True, out, devices, device_map, self.dev_type
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
                            }
                            if dev_map["type"] in self.dev_type.keys():
                                self.dev_type[dev_map["type"]].append(dev_map["name"])
                                device_map.update({device["name"]: dev_map})

                        self.NVMe_BDF = device_map
                        self.system_disks = [
                            item
                            for item in device_map
                            if device_map[item]["class"].lower() == "system"
                            and device_map[item]["type"].lower() == "ssd"
                        ]
                        self.system_buffer = [
                            item
                            for item in device_map
                            if device_map[item]["class"].lower() == "system"
                            and device_map[item]["type"].lower() == "nvram"
                        ]
                        return (
                            True,
                            out,
                            devices,
                            device_map,
                            self.dev_type["NVRAM"],
                            self.dev_type["SSD"],
                            self.system_disks,
                        )
                else:
                    raise Exception(
                        "list dev command failed with status code {}".format(
                            out["status_code"]
                        )
                    )
            else:
                raise Exception("list dev command failed with error {}".format(out))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, None, None, None, None

    def smart_device(self, devicename):
        """
        method to get smart details of a devce
        Args:
            device_name : name of the device
        Returns:
            bool, dict()
        """
        try:
            cmd = "smart-log -d {}".format(devicename)
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ################################################logger##############################
    def set_log_level_logger(self, level):
        """
        method to set the log level
        Args:
            level (str) : logger level
        Returns:
            bool, list()
        """
        try:
            cmd = "set-level --level {}".format(level)
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def get_log_level_logger(self):
        """
        method to get the log level
        Returns:
            bool, list
        """
        
        try:
            cmd = "get-level"
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def apply_log_filter(self):
        """
        method to set log filter
        Returns:
            bool, list
    """
        try:
            cmd = "apply-filter"
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def info_logger(self):
        """
        method to get logger info 
        Returns:
            bool, list
        """
        try:
            cmd = "info"
            cli_error, jout = self.run_cli_command(cmd, command_type="logger")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ###################################################telemetry#########################

    def start_telemetry(self):
        """
        method to start telemetry
        Returns:
            bool, list
        """
        try:
            cmd = "start"
            cli_error, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def stop_telemetry(self):
        """
        method to stop telemetry
        Returns:
            bool, list
        """
        try:
            cmd = "stop"
            cli_error, jout = self.run_cli_command(cmd, command_type="telemetry")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ###################################################QOS##############################
    def create_volume_policy_qos(
        self,
        volumename,
        arrayname,
        maxiops,
        maxbw,
        miniops = None,
        minbw = None,
    ) :
        """
        method to create qos volume policy
        Args:
            volumename (str) : name of the volume
            arrayname (str) : name of the array
            maxiops (str) IOPs value
            maxbw (str) bandwidth
            miniops (str)
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
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def reset_volume_policy_qos(
        self, volumename, arrayname
    ):
        """method to reset volume policy
        Args:
            volumename (str) name of the volume
            arrayname (str) name of the array
        Returns:
            bool, list
        """
        try:
            cmd = "reset -v {} -a {}".format(volumename, arrayname)
            cli_error, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def list_volume_policy_qos(self, volumename, arrayname):
        """
        method to list volume policy
        Args:
            volumename (str) : name of the volume
            arrayname (str) : name of the array
        Returns:
            bool, list
        """
        try:
            cmd = "list -v {} -a {}".format(volumename, arrayname)
            cli_error, jout = self.run_cli_command(cmd, command_type="qos")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    ###################################################volume#############################
    def list_volume(self, array_name = None) :
        """
        Method to list volumes
        Args:
            array_name : name of the array
        Returns:
            (bool, list, dict())
        """
        try:
            if array_name != None:
                self.array_name = array_name
            vol_dict = {}
           
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
                vol_dict[vol["name"]] = {
                    "total": vol["total"],
                    "status": vol["status"],
                    "max_iops": vol["maxiops"],
                    "maxbw": vol["maxbw"],
                }
            self.vols = list(vol_dict.keys())
            return True, list(vol_dict.keys()), vol_dict
        except Exception as e:
            logger.error("list volume command failed with exception {}".format(e))
            return False, out

    def create_volume(
        self,
        volumename,
        size,
        array_name= None,
        iops = 0,
        bw = 0,
    ):
        """
        Method to create volume
        Args:
            volumename (str) : name of the volume
            size (str) : size of the volume
            array_name (str) : name of the array
            iops (str) : iops value
            bw (str) : bandwidth value 
            #TODO add max and min iops
        Returns:
            bool, list()
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = " create -v {} --size {} --maxiops {} --maxbw {} -a {} ".format(
                volumename, size, iops, bw, array_name
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def delete_volume(self, volumename, array_name):
        """
        Method to delete volume
        Args:
            volumename (str) : name of the volume
            array_name (str) : name of the array
        Returns:
            bool, list
        """
        try:
            cmd = "delete -a {} -v {} --force ".format(array_name, volumename)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def mount_volume(
        self, volumename, array_name, nqn = None
    ) :
        """
        Method to mount volume
        Args:
            volumename (str) name of the volume
            array_name (str) name of the array
            nqn (str) Subsystem name 
        Returns:
            bool, list
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
        self, new_volname = None, volname= None, array_name = None
    ) :
        """
        Method to unmount volume
        Args:
            new_volname (str) name of the new volume
            volname (str) old volumename
            array_name (str) old array_name
        Returns:
            bool, list
        """
        try:
            cmd = "rename --volume-name {} --array-name {} --new-volume-name {}".format(
                volname, array_name, new_volname
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def unmount_volume(self, volumename, array_name) :
        """
        Method to unmount volume
        Args:
            volumename (str) name of the volume
            array_name (str) name of array
        Returns:
            bool, list
        """
        try:
            cmd = "unmount -v {} -a {} --force".format(volumename, array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    def mount_with_subsystem_volume(
        self, volumename, nqn_name, array_name, ip, vcid
    ):
        """
        method to mount volume with subsystem
        Args:
            volumename (str) name of the volume
            nqn_name (str) : name of the SS
            array_name (str) name of the array
            ip (str) : IP details
            vcid (str) : port details
        Returns:
            bool, list
            
        """
        try:
            cmd = "mount-with-subsystem --volume-name {} --subnqn {} --array-name {} --trtype tcp --traddr {} --trsvcid {} --force".format(
                volumename, nqn_name, array_name, ip, vcid
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False, jout

    #########################################subsystem#################
    def create_subsystem(
        self,
        nqn_name,
        ns_count= 512,
        s = "POS000000000001",
        d = "POS_VOLUME",
    ) :
        """
        Method to create nvmf subsystem
        Args:
            nqn_name (str) : name of Subsystem
            ns_count (int) : max namespace
            d (str) : model_number
            s (str) : serial number
        Returns:
            bool, list()
        """
        try:
            cmd = "create --subnqn {} --serial-number {} --model-number {} --max-namespaces {} --allow-any-host".format(
                nqn_name, s, d, ns_count
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def list_subsystem(self) :
        """
        method executes nvmf_get_subsystems
        Returns:
            bool, list
        """
        try:
            nvmf_out, temp = {}, {}
            out = self.run_cli_command("list", command_type="subsystem")
            for data in out[1]["data"]["subsystemlist"]:
                temp = data
                nvmf_out[data["nqn"]] = temp
            logger.info(nvmf_out)
            return (True, nvmf_out)

        except Exception as e:
            logger.error("Get_nvmf_subsystem failed due to %s" % e)
            return (False, None)

    def add_listner_subsystem(
        self, nqn_name: str, mellanox_interface: str, port: str, transport: str = "TCP"
    ) :
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
                if jout["status_code"] == 0:
                    return cli_error, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def create_transport_subsystem(
        self,
        buf_cache_size = 64,
        num_shared_buf = 4096,
        transport_type = "TCP",
    ) :
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
            out = self.run_cli_command(command, command_type="subsystem")

            if out[0] == True:
                if out[1]["status_code"] == 0:
                    return True, out
        except Exception as e:
            logger.error(e)
            return False, out

    def delete_subsystem(self, nqn_name , force=True):
        """method to delete subsystem
        Args:
            nqn_name (str) name of the subsystem
            force (bool) |default True
        Returns:
            bool, list
        """
        try:
            force = " --force" if force else " "
            command = f"delete --subnqn {nqn_name} {force}"
            cli_error, jout = self.run_cli_command(command, "subsystem")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")

        except Exception as e:
            logger.error(e)
            return False, jout
    #TODO check if the below Methods are to be open sourced/ renamed for open sourcing
    ######################################wbt#######################################

    def wbt_do_gc(self, array_name: str = None) :
        """
        Method to do gc
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "do_gc -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
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
            cmd = "get_gc_status -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.error(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
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
            cmd = "get_gc_threshold -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return False, jout

    def wbt_flush(self, array_name: str = None) :
        """
        Method to flush
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "flush -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
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

    def wbt_read_stripemap_entry(
        self, vsid: str, array_name: str = None
    ) :
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
