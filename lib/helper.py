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

import json
import logger
import re
import string
import random
import math
import datetime

logger = logger.get_logger(__name__)


class Helper:

    """helper methods for target and initiator"""

    def __init__(self, ssh_obj):
        self.ssh_obj = ssh_obj
        self.cli_history = []
        self.sys_memory_list = []
        self.ip_addr = []

    def json_reader(self, json_file) -> (bool):
        """ "method to read and return Json dict"""

        try:
            # dir_path = os.path.dirname(os.path.realpath(__file__))

            with open(f"{json_file}") as f:
                static_dict = json.load(f)
            f.close()
            self.static_dict = static_dict

            return True

        except OSError as e:
            logger.error(f"json read failed due to {e}")
            return False

    def set_MTU_mel(self, MTU: str = "9000") -> bool:
        """
        Method to mellanox interface ip
        """
        self.get_mellanox_interface_ip()
        if len(self.cnctd_mlx_inter) is 0:
            logger.error("No interfaces found")
            return False

        cmd = "ifconfig {} mtu {}".format(self.cnctd_mlx_inter[0].strip(), MTU)
        self.ssh_obj.execute(cmd)

        v_cmd = "ifconfig {} | grep mtu".format(self.cnctd_mlx_inter[0].strip())
        out = self.ssh_obj.execute(v_cmd)

        if "{}".format(MTU) in out[0]:
            logger.info(
                "MTU {} set for {}".format(MTU, self.cnctd_mlx_inter[0].strip())
            )
            return True
        else:
            logger.error("failed to set MTU ")
            return False

    def set_eth_speed(self, Speed: str = 1000) -> bool:
        """
        Method to set ethool speed
        """
        try:
            self.get_mellanox_interface_ip()
            if len(self.cnctd_mlx_inter) is 0:
                logger.error("No interfaces found")
                return False

            v_cmd = "ethtool {} | grep Speed".format(self.cnctd_mlx_inter[0].strip())
            out = self.ssh_obj.execute(v_cmd)
            reg = "[0-9]+"
            se = re.search(reg, out[0])
            speed = se.group()
            logger.info(
                "Speed of {} is {}MB/s".format(
                    self.cnctd_mlx_inter[0].strip(), str(speed)
                )
            )
            if int(str(speed)) == Speed:
                logger.info("Speed already set to {}".format(Speed))
                return True
            else:
                logger.info(str(Speed))
                cmd = "ethtool -s {} speed {} autoneg off".format(
                    self.cnctd_mlx_inter[0].strip(), str(Speed)
                )
                out = self.ssh_obj.execute(cmd)
                out = self.ssh_obj.execute(v_cmd)
                se = re.search(reg, out[0])
                speed = se.group()

                if int(speed) is Speed:
                    return True

        except Exception as e:
            logger.error("Not able to set the speed due to {}".format(e))
            return False

    def ping_test(self, mlx_ip: str) -> bool:
        """
        Method to test pinging the ip
        """
        try:
            cmd = "ping -M do -s 8972 -c 5 {}".format(mlx_ip)
            out = self.ssh_obj.execute(cmd, get_pty=True, expected_exit_code=0)
            Packet_loss = int(
                [i for i in out if "transmitted" in i and "packet loss" in i][0]
                .split(" ")[5]
                .strip()
                .split("%")[0]
            )
            if Packet_loss >= 1:
                logger.error("Packet loss during Ping")
                return False
            else:
                return True
        except Exception as e:
            logger.error(" error ocured due to {}".format(e))
            return False

    def get_mellanox_interface_ip(self) -> (bool, list):
        """
        Method to get mellanox interface ip
        """
        try:
            mlx_inter = []

            self.cnctd_mlx_inter = []

            cmd = "ls /sys/class/net"

            out = self.ssh_obj.execute(cmd)

            for inter in out:
                if inter.strip() != "lo":
                    cmd = "ethtool -i {} | grep  driver:".format(inter.strip())
                    mlx_out = self.ssh_obj.execute(cmd)
                    if "mlx" in str(mlx_out[0]):
                        mlx_inter.append(inter)
                        status_cmd = "cat /sys/class/net/{}/operstate".format(
                            inter.strip()
                        )
                        port_status = self.ssh_obj.execute(status_cmd)
                        if port_status[0].strip() == "up":
                            self.cnctd_mlx_inter.append(inter.strip())

            for c_iner in self.cnctd_mlx_inter:
                cmd = "ifconfig {} | grep inet".format(c_iner.strip())
                try:
                    inet_out = self.ssh_obj.execute(cmd.strip())
                    ip_address = re.search(
                        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", inet_out[0]
                    ).group()
                    if ip_address:
                        self.ip_addr.append(ip_address)
                except:
                    logger.warn(
                        "IP is not assigned to the connected mellanox interface {} ".format(
                            c_iner.strip()
                        )
                    )
            logger.info(
                "Connected Mellanox interfaces are {} ".format(self.cnctd_mlx_inter)
            )
            if len(self.ip_addr) == 0:
                raise Exception("Ip is not assigned to any of the Mellanox")

        except Exception as e:
            logger.error("Get_mel_IP failed due to {}".format(e))
            return (False, None)
        return (True, self.ip_addr)

    def port_up_down(self, port_list: list, action: str) -> bool:
        """
        Method to port up or down
        """
        try:

            if "up" in action or "down" in action:
                for port in port_list:
                    cmd = "ifconfig {} {}".format(port, action)
                    self.ssh_obj.execute(cmd)
                return True
            else:
                raise Exception(
                    "No required action mentioned. Please specify Up or down"
                )
        except Exception as e:
            logger.error("Port manipulation failed due to {}".format(e))
            return False

    def random_File_name(self) -> str:
        """
        Method to generate random file name
        """
        letters = string.ascii_lowercase
        Name = "".join(random.choice(letters) for i in range(15))
        datetime_object = datetime.now()
        date = (str(datetime_object).replace(" ", "-")).split(".")[0].replace(":", "-")

        return Name + "_" + date

    def check_pos_exit(self) -> bool:

        """method to check pos running status
        if pos is not running returns True else False
        """
        command = "ps -aef | grep -i poseidonos"
        out = self.ssh_obj.execute(command)
        ps_out = "".join(out)
        if "bin/poseidonos" not in ps_out:
            return True
        else:
            return False

    def wbt_parser(self, file_name: str) -> (bool, dict()):
        """
        Method to wbt parser
        """
        try:
            logger.info("parsing Output")
            parse_cmd = "cat %s" % file_name
            out = self.ssh_obj.execute(parse_cmd)
            map_dict, temp = {}, []
            for par in out:
                if ":" in par:
                    temp = par.split(":")
                    temp_name = temp[0].lower()
                    temp_name.replace(" ", "_")
                    map_dict[temp_name] = temp[1].strip()
            return True, map_dict
        except Exception as e:
            logger.error("Failed due to the following error : {}".format(e))
            return False

    def convert_size(self, size_bytes: int) -> str:
        """
        Method to convert size
        """
        if size_bytes == 0:
            return "0B"

        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "{} {}".format(s, size_name[i])

    def check_system_memory(self):
        """
        Method to chect memory status
        """
        try:
            cmd = "cat /proc/meminfo"
            out = self.ssh_obj.execute(cmd)

            sys_memory = dict()
            sys_memory["time"] = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

            for mem_entry in out:
                if "memtotal" in mem_entry.lower():
                    sys_memory["memtotal"] = (
                        re.search(": (.+?) kB", mem_entry).group(1).strip()
                    )
                elif "memfree" in mem_entry.lower():
                    sys_memory["memfree"] = (
                        re.search(": (.+?) kB", mem_entry).group(1).strip()
                    )
                elif "memavailable" in mem_entry.lower():
                    sys_memory["memavailable"] = (
                        re.search(": (.+?) kB", mem_entry).group(1).strip()
                    )
                elif "hugepages_total" in mem_entry.lower():
                    sys_memory["hugepages_total"] = mem_entry.split(":")[1].strip()
                elif "hugepages_free" in mem_entry.lower():
                    sys_memory["hugepages_free"] = mem_entry.split(":")[1].strip()
            logger.info(
                "[{}] {} MemTotal: {}, MemFree: {}, MemAvailable: {}, HugePages_Total: {}, HugePages_Free: {}".format(
                    self.ssh_obj.hostname,
                    sys_memory["time"],
                    sys_memory["memtotal"],
                    sys_memory["memfree"],
                    sys_memory["memavailable"],
                    sys_memory["hugepages_total"],
                    sys_memory["hugepages_free"],
                )
            )
            if len(self.sys_memory_list) > 5000:
                del self.sys_memory_list[0]
            self.sys_memory_list.append(sys_memory)

            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def add_cli_history(self, parse_out):
        """
        Method to get cli command history for debugging
        """
        if len(self.cli_history) > 100:
            del self.cli_history[0]
        self.cli_history.append(
            [
                parse_out["command"],
                parse_out["status_code"],
                parse_out["params"],
                parse_out["data"],
            ]
        )
        return True

    def parse_out(self, jsonout, command):

        out = json.loads(jsonout)
        command = command
        if "param" in out.keys():
            param = out["Request"]["param"]
        else:
            param = {}
        # logger.info(out)
        status_code = out["Response"]["result"]["status"]["code"]
        description = out["Response"]["result"]["status"]["description"]
        logger.info(
            "status code response from the command {} is {}".format(
                command, status_code
            )
        )
        logger.info(
            "DESCRIPTION reposonse from command {} is {}".format(command, description)
        )

        if "data" in out["Response"]["result"]:
            return {
                "output": out,
                "command": command,
                "status_code": status_code,
                "description": description,
                "data": out["Response"]["result"]["data"],
                "params": param,
            }
        else:
            return {
                "output": out,
                "command": command,
                "status_code": status_code,
                "description": description,
                "params": param,
                "data": None,
            }
