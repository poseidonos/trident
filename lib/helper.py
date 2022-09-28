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
import os
import codecs
import itertools

logger = logger.get_logger(__name__)

QDValues = [1, 4, 16, 32, 128, 256]
IOSizes = ["4K", "8K", "32K", "256K", "1M", "2M", "16M", "32M"]
BSSplit = ["4K/90:8K/10", "4K/70:8K/30", "4K/50:8K/50", "4K/30:8K/70"]
ReadWrite = ["readwrite", "randrw"]
WRPerc = [100, 75, 50, 25]
Direct = [0, 1]
Unalign = [0, 1]
SEQ = 0
fio = None


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
            dir_path = os.path.dirname(os.path.realpath(__file__))
            json_path = f"{dir_path}/../testcase/config_files/topology.json"
            self.json_reader(json_path)

            if self.static_dict["login"]["target"]["server"][0]["Data_Ip"] != "None":
                self.ip_addr = [
                    self.static_dict["login"]["target"]["server"][0]["Data_Ip"]
                ]
                return (True, self.ip_addr)

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
            logger.info("POS IS NOT RUNNING")
            return True
        else:
            logger.warning("POS IS RUNNING")
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

    def generate_pattern(self, num_digits):
        """
        Method to generate random number of given num_digits digits
        """
        try:
            pattern = codecs.encode(os.urandom(int(num_digits / 2)), "hex").decode()
        except:
            logger.info("could not generate pattern!!!")
            raise Exception("could not generate pattern!!!")
        return pattern

    def generate_simple_testcases(self, fs_mode):
        """
        Method to make fio commandlines
        """
        my_tests = []
        fioranges = [WRPerc[0:2], ReadWrite]
        bsqdrange = [[2**p for p in range(14, 20)], [2**p for p in range(8, 11)]]
        for rc, rd in itertools.product(*fioranges):
            for bs, qd in itertools.product(*bsqdrange):
                pattern = "0x" + "".join(
                    random.choice("0123456789abcdef") for i in range(16)
                )
                _dict = {
                    "rw": rd,
                    "verify_pattern": pattern,
                    "iodepth": qd,
                    "rwmixwrite": rc,
                    "do_verify": 1,
                    "bs": bs,
                }
                if int(rc) == 100:
                    _dict.update({"do_verify": 0})
                    my_tests.append((_dict))
                    _rdict = dict(_dict)
                    _rdict.update({"rwmixwrite": 0, "do_verify": 1})
                    my_tests.append((_rdict))
                else:
                    my_tests.append((_dict))
        return my_tests

    def get_nonmix_tests(self, fs_mode):
        _tests = []
        fioranges = [Unalign, Direct, ReadWrite, WRPerc, IOSizes, QDValues]
        for (
            unalg,
            d,
            rd,
            rc,
            ios,
            qd,
        ) in itertools.product(*fioranges):
            if unalg and d:
                continue
            bssplit = random.choice(BSSplit)
            pattern = "0x" + "".join(
                random.choice("0123456789abcdef") for i in range(16)
            )
            _dict = {
                "rw": rd,
                "verify_pattern": pattern,
                "io_size": ios,
                "iodepth": qd,
                "rwmixwrite": rc,
                "do_verify": 1,
            }
            if unalg:
                _dict.update({"bsrange": "4K-8K", "bs_unaligned": "", "direct": 0})
            if fs_mode and int(rc) != 100:
                _dict.update({"experimental_verify": 1})
            else:
                _dict.update({"bssplit": bssplit, "direct": d})
            if int(rc) == 100:
                _dict.update({"do_verify": 0})
                _tests.append((_dict))
                _rdict = dict(_dict)
                _rdict.update({"rwmixwrite": 0, "do_verify": 1})
                _tests.append((_rdict))
            else:
                _tests.append((_dict))
        return _tests

    def get_mixedio_tests(self, fs_mode):

        _tests = []
        qd = "256"
        _IOSizes = ["4K:32M", "8K:16M", "32M:4K", "16M:8K"]
        fioranges = [Unalign, Direct, ReadWrite, ReadWrite, _IOSizes]
        for unalg, d, o_rd, i_rd, ioset in itertools.product(*fioranges):
            if unalg and d:
                continue
            s_io = ioset.split(":")[0]
            b_io = ioset.split(":")[1]
            bssplit = random.choice(BSSplit)
            pattern = "0x" + "".join(
                random.choice("0123456789abcdef") for i in range(16)
            )
            _dict = {
                "rw": o_rd,
                "verify_pattern": pattern,
                "io_size": s_io,
                "iodepth": qd,
                "rwmixwrite": 50,
                "do_verify": 1,
            }
            if unalg:
                _dict.update({"bsrange": "4K-8K", "bs_unaligned": "", "direct": 0})
            if fs_mode:
                _dict.update({"experimental_verify": 1})
            else:
                _dict.update({"bssplit": bssplit, "direct": d})
            _tests.append((_dict))

            bssplit = random.choice(BSSplit)
            pattern = "0x" + "".join(
                random.choice("0123456789abcdef") for i in range(16)
            )
            _ndict = {
                "rw": i_rd,
                "verify_pattern": pattern,
                "io_size": b_io,
                "iodepth": qd,
                "rwmixwrite": 50,
                "do_verify": 1,
            }
            if unalg:
                _ndict.update({"bsrange": "4K-8K", "bs_unaligned": "", "direct": 0})
            if fs_mode:
                _ndict.update({"experimental_verify": 1})
            else:
                _ndict.update({"bssplit": bssplit, "direct": d})
            _tests.append((_ndict))
        return _tests

    def generate_fio_testcases(self, fs_mode):
        my_tests = []
        if not fs_mode:
            my_tests.append(
                (
                    {
                        "rw": "trim",
                        "bs": "4k",
                        "io_size": "32M",
                        "iodepth": 32,
                        "trim_verify_zero": 1,
                    }
                )
            )
        my_tests.extend(self.get_nonmix_tests(fs_mode))
        if not fs_mode:
            my_tests.append(
                (
                    {
                        "rw": "randtrim",
                        "bs": "4k",
                        "io_size": "4K",
                        "iodepth": 64,
                        "trim_verify_zero": 1,
                    }
                )
            )
            my_tests.append(
                (
                    {
                        "rw": "randtrim",
                        "bs": "4k",
                        "io_size": "32M",
                        "iodepth": 32,
                        "trim_verify_zero": 1,
                    }
                )
            )
        my_tests.extend(self.get_mixedio_tests(fs_mode))
        if not fs_mode:
            my_tests.append(
                (
                    {
                        "rw": "randtrim",
                        "bs": "4k",
                        "io_size": "4k",
                        "iodepth": 64,
                        "trim_verify_zero": 1,
                    }
                )
            )
        my_tests.extend(self.generate_simple_testcases(fs_mode))
        return my_tests

    def generate_fio_commandline(self, argdict, fs_mode):
        """Generate FIO command line string from argdict."""
        json_file = "fio_raw_gen.json" if not fs_mode else "fio_fs_gen.json"
        json_loc = f"../testcase/config_files/{json_file}"
        assert self.json_reader(json_loc) == True
        argdict = {**self.static_dict, **argdict}
        if ("rw" in argdict) and ("readwrite" in argdict):
            logger.debug("FIO 'rw' argument overwriting 'readwrite'")
        # convert key:value pairs to sorted argument=value list
        parms = []
        for key, value in argdict.items():
            if value is not None:
                item = "--" + key
                if value != "":
                    item += f"={value}"
                parms.append(item)
        parms.sort()
        # build and return FIO cmd line
        return ('fio' + ' ' + ' '.join(parms))


    def _get_sized_drives(elf, devices: dict) -> dict:
        """
        Create a device dictionary based on size
        return device list as value for size key
        {"Size": ["unvme-ns-0", "unvme-ns-1"]
        """
        device_size_dict = {}
        for dev_name, dev in devices.items():
            if dev["type"].lower() != "ssd" or dev["class"].lower() == "array":
                continue

            size = int(dev["size"] // (1024 * 1024 * 1024))  # Convert in GiB
            size = f"{size}GiB"
            try:
                device_size_dict[size].append(dev_name)
            except:
                device_size_dict[size] = [dev_name]

        return device_size_dict

    def _get_sized_disks(self, device_size_dict: dict, device_select: dict):
        selected_devices = []
        for dev_size, num_device in device_select.items():
            if dev_size.lower() in ("any", "mix"):
                continue

            device_list = device_size_dict.get(dev_size, [])

            if len(device_list) < num_device:
                logger.error(
                    "Only {} devices of {} size are available. "
                    "But {} drives are required.".format(
                        len(device_list), dev_size, num_device
                    )
                )
                return False, selected_devices

            for i in range(num_device):
                dev_name = device_size_dict[dev_size].pop(0)
                selected_devices.append(dev_name)

        return True, selected_devices

    def _get_remaining_disks(self, device_size_dict: dict, device_select: dict):
        selected_devices = []
        for dev_type in ("mix", "any"):
            device_types = [
                dev_size for dev_size, dev_list in device_size_dict.items() if dev_list
            ]
            device_count = sum(len(dev_list) for dev_list in device_size_dict.values())
            num_device = device_select.get(dev_type, 0)
            if num_device == 0:
                continue

            if dev_type == "mix" and len(device_types) < num_device:
                logger.error(
                    "Only {} device types are available. But {} are "
                    "required.".format(len(device_types), num_device)
                )
                return False, device_select
            elif dev_type == "any" and device_count < num_device:
                logger.error(
                    "Only {} devices are available. But {} are "
                    "required.".format(device_count, num_device)
                )
                return False, device_select

            counter = 0
            while counter < num_device:
                for dev_type in device_size_dict.keys():
                    if counter == num_device:
                        break
                    if device_size_dict[dev_type]:
                        dev_name = device_size_dict[dev_type].pop(0)
                        selected_devices.append(dev_name)
                        counter += 1

        return True, device_select

    def select_hetro_devices(
        self, devices: dict, data_dev_select: dict, spare_dev_select: dict = None
    ) -> tuple:
        """
        Helper function to select Hetero devices of different size based on
        select params for data disk and spare disk.
        Select Param -> Number of disk. e.g:
        '20GiB' : 4 => 4 disk of 20 GiB size
        'mix' : 4 => 4 disk of all mix size
        'any' : 2 => 2 disk of any size
        """
        selected_devices = {"data_dev_list": [], "spare_dev_list": []}

        device_size_dict = self._get_sized_drives(devices)

        logger.info(f"Available devices: {device_size_dict}")
        logger.info(f"Requested data drives: {data_dev_select}")
        logger.info(f"Requested spare drives: {spare_dev_select}")

        # Select the data device based on size
        res, device_list = self._get_sized_disks(device_size_dict, data_dev_select)
        if not res:
            return False, selected_devices
        selected_devices["data_dev_list"].extend(device_list)

        if spare_dev_select != None:
            # Select the spare device based on size
            res, device_list = self._get_sized_disks(device_size_dict, spare_dev_select)
            if not res:
                return False, selected_devices
            selected_devices["spare_dev_list"].extend(device_list)

        # Select the data device of mix/different sizes
        res, device_list = self._get_remaining_disks(device_size_dict, data_dev_select)
        if not res:
            return False, selected_devices
        selected_devices["data_dev_list"].extend(device_list)

        logger.info(f"Selected data device: {selected_devices['data_dev_list']}")

        if spare_dev_select != None:
           # Select the spare device of any and mix/differnt size
            res, device_list = self._get_remaining_disks(device_size_dict, spare_dev_select)
            if not res:
                return False, selected_devices
            selected_devices["spare_dev_list"].extend(device_list)

            logger.info(f"Selected spare device: {selected_devices['spare_dev_list']}")
        return True, selected_devices
