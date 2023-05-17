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

import array
from datetime import datetime
import time
import re
import traceback
import helper
import logger
from cli import Cli
import copy
import pytest
logger = logger.get_logger(__name__)

class TargetUtils:
    """
    The Class objects will contain supporting methods to configure POS

    Arguments:
        ssh_obj : ssh obj of the Target
        data_dict (dict) : path for POS config
    """

    def __init__(self, ssh_obj: object, cli_obj: object,
                 data_dict: dict, pos_as_service: bool = True):
        """ 
        TODO
        """
        self.ssh_obj = ssh_obj
        self.static_dict = data_dict
        self.pos_as_service = pos_as_service
        
        self.cli = cli_obj
        # self.array = array_name
        self.helper = helper.Helper(ssh_obj, pos_as_service= self.pos_as_service)
        self.udev_rule = False
        self.total_required = 0
        assert self.helper.get_mellanox_interface_ip()[0] == True

    def generate_nqn_name(self, default_nqn_name: str = "nqn.2022-10.pos") -> str:
        """
        Method to generate nqn name
        Args:
            default_nqn_name (str) : name of the subsystem
        Returns:
            str
        """
        assert self.cli.subsystem_list()[0] == True
        ss_list = list(self.cli.nvmf_subsystem.keys())
        
        num = len(ss_list)
        if num == 1:
            logger.info("creating first Nvmf Subsystem")
            return "{}:subsystem1".format(default_nqn_name)
        elif num == 0:
            logger.error("No subsystem found, please verify pos status")
            return None
        else:
            temp = ss_list
            temp.remove("nqn.2014-08.org.nvmexpress.discovery")
            count = []
            for subsystem in temp:
                c = int(re.findall("[0-9]+", subsystem)[3])
                count.append(c)
            next_count = max(count) + 1
            new_ss_name = "{}:subsystem{}".format(default_nqn_name, next_count)
            logger.info("subsystem name is {}".format(new_ss_name))
        return new_ss_name

    def dev_bdf_map(self) -> (bool, dict()):
        """
        Method to get device address
        Returns:
            bools, dict
        """
        try:
            dev_bdf_map = {}
            self.cli.device_list()
            if len(self.cli.dev_type["SSD"]) == 0:
                raise Exception("No Devices found")
            for dev in list(self.cli.NVMe_BDF.keys()):
                dev_bdf_map[dev] = self.cli.NVMe_BDF[dev]["addr"]

        except Exception as e:
            logger.error("Execution failed with exception {}".format(e))
            return False, None
        return True, dev_bdf_map

    def device_hot_remove(self, device_list: list) -> bool:
        """
        Method to hot remove devices
        Args:
            device_list : list of devices to be removed
        Returns:
            bool
        """
        try:
            self.dev_addr = []
            self.cli.device_list()
            for each_dev in device_list:
                if each_dev not in self.cli.dev_type["SSD"]:
                    logger.error(f"Device {each_dev} is not connected")
                    return False

            dev_map = self.dev_bdf_map()
            if dev_map[0] == False:
                logger.info("failed to get the device and bdf map")
                return False

            for dev in device_list:
                pci_addr = dev_map[1][dev]
                self.dev_addr.append(pci_addr)
                logger.info(f"PCIe address {pci_addr} of given device {dev}")

                command = f"echo 1 > /sys/bus/pci/devices/{pci_addr}/remove"
                logger.info(f"Executing hot plug command {command}")
                self.ssh_obj.execute(command)

                for i  in range(10):
                    wait_time = 3  # 3 seconds
                    logger.info(f"Wait {wait_time} seconds...")
                    time.sleep(wait_time)
                    list_dev_out = self.dev_bdf_map()
                    if list_dev_out[0] == False:
                        logger.error("Failed to get bdf map after disk remove")
                        return False

                    if pci_addr not in list(list_dev_out[1].values()):
                        break

                    logger.info(f"Removed device {dev} is still listed")

                if pci_addr in list(list_dev_out[1].values()):
                    logger.warning(f"Failed to hot plug the device {dev}")

                assert self.cli.device_list()[0] == True
                if dev in self.cli.dev_type["SSD"]:
                    logger.error(f"Failed to remove the device {dev}")
                    return False
                    
                logger.info(f"Successfully removed the device {dev}")
            return True
        except Exception as e:
            logger.error(f"Device hot remove failed due to {e}")
            return False

    def device_hot_remove_by_bdf(self, bdf_addr_list: list) -> bool:
        """
        Method to remove device using bdf address
        Args:
            bdf_add_list (list) : list of bdf to be removed
        Returns:
            bool
        """
        try:
            self.dev_addr = bdf_addr_list
            addr_list = self.get_nvme_bdf()
            for each_addr in bdf_addr_list:
                if each_addr not in addr_list[1]:
                    addr = each_addr.strip()
                    logger.error(f"Nvme device not found with the bdf {addr}")
                    return False

                logger.info("Removing the bdf : {}".format(each_addr))
                hot_plug_cmd = "echo 1 > /sys/bus/pci/devices/{}/remove ".format(
                    each_addr.strip()
                )
                logger.info("Executing hot plug command {} ".format(hot_plug_cmd))
                self.ssh_obj.execute(hot_plug_cmd)
                bdf_list = self.get_nvme_bdf()
                if bdf_list[0] == False:
                    logger.error("failed to get the nvme device bdf")
                    return False
                if each_addr in bdf_list[1]:
                    logger.error(
                        "failed to hot plug the device with bdf : {} ".format(
                            each_addr.strip()
                        )
                    )
                    return False
                else:
                    logger.info(
                        "Successfully removed the device with bdf :{} ".format(
                            each_addr.strip()
                        )
                    )
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False
        return True

    def get_nvme_bdf(self) -> (bool, list):
        """
        Method to get nvme bdf address
        Returns:
            bool, list
        """
        try:
            logger.info("feteching the nvme device bdf")
            bdf_cmd = "lspci -D | grep 'Non-V' | awk '{print $1}'"
            bdf_out = self.ssh_obj.execute(bdf_cmd)
            logger.info("bdf's for the connected nvme drives are {} ".format(bdf_out))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, None
        return True, bdf_out

    def re_scan(self):
        """method to do pci scan with out POS"""
        re_scan_cmd = "echo 1 > /sys/bus/pci/rescan "
        self.ssh_obj.execute(re_scan_cmd)
        return True

    def pci_rescan(self):
        """
        Method to pci rescan
        Returns:
            bool
        """
        try:
            logger.info("Executing list dev command before rescan")
            list_dev_out_bfr_rescan = self.dev_bdf_map()
            logger.info(
                "No. of devices before rescan: {} ".format(
                    len(list_dev_out_bfr_rescan[1])
                )
            )

            assert self.re_scan() == True

            logger.info("scanning the devices after rescan")
            time.sleep(5)  # Adding 5 sec sleep for the sys to get back in normal state
            assert self.cli.device_scan()[0] == True

            list_dev_out_aftr_rescan = self.dev_bdf_map()
            if list_dev_out_aftr_rescan[0] == False:
                logger.error("failed to get the device and bdf map after pci rescan")
                return False
            logger.info(
                "No. of devices after rescan: {} ".format(
                    len(list_dev_out_aftr_rescan[1])
                )
            )
            if (len(list_dev_out_aftr_rescan[1])) < (len(list_dev_out_bfr_rescan)):
                logger.error("After rescan the removed device didn't get detected ")
                return False
        except Exception as e:
            logger.error(
                "pci rescan command execution failed with exception {}".format(e)
            )
            return False
        return True

    def udev_install(self) -> bool:
        """
        Method to udev install
        Returns:
            bool
        """
        try:
            logger.info("Running udev_install command")
            cmd = "cd {} ; make udev_install ".format(self.cli.pos_path)
            udev_install_out = self.ssh_obj.execute(cmd)
            out = "".join(udev_install_out)
            logger.info(out)
            match = [
                data
                for data in udev_install_out
                if "update udev rule file" in data or "copy udev bind rule file" in data
            ]
            if match:
                logger.info("Successfully executed the make udev_install command")
                return True
            else:
                logger.error("failed to execute make udev_install command")
                return False
        except Exception as e:
            logger.info("command execution failed with exception  {}".format(e))
            return False

    def get_hetero_device(
        self,
        data_device_config: dict,
        spare_device_config: dict = None,
        device_scan=False,
        device_list=True,
    ) -> bool:
        """
        Method to create array using hetero devices
        data_device_config: {dev_size: num_dev; '20GiB': 1}
        Returns:
            bool
        """
        if device_scan:
            if not self.cli.device_scan():
                logger.error("Failed to get the device list")
                return False

        if device_list:
            if not self.cli.device_list():
                logger.error("Failed to get the device list")
                return False

        device_scan = self.cli.NVMe_BDF

        res, devices = self.helper.select_hetro_devices(
            devices=device_scan,
            data_dev_select=data_device_config,
            spare_dev_select=spare_device_config,
        )

        if res == False:
            logger.error("Failed to select required hetero data device")
            return False

        total_data_dev = sum(data_device_config.values())

        if total_data_dev != len(devices["data_dev_list"]):
            logger.info(f"Selected data devices: {devices['data_dev_list']}")
            logger.error("Failed to select required hetero data device")
            return False

        if spare_device_config:
            total_spare_dev = sum(spare_device_config.values())
            if total_spare_dev != len(devices["spare_dev_list"]):
                logger.info(f"Selected spare devices: {devices['spare_dev_list']}")
                logger.error("Failed to select required hetero spare device")
                return False

        self.data_drives = devices["data_dev_list"]
        self.spare_drives = devices["spare_dev_list"]
        return True

    def check_rebuild_status(self, array_name: str = None, rebuild_progress=100) -> bool:
        """
        Method to check rebuild status
        Args:
            array_name (str) "name of the array" (optional)
        Returns:
            bool
        """
        try:
            if array_name == None:
                array_name = self.array

            if self.cli.array_info(array_name=array_name)[0]:
                situation = self.cli.array_data[array_name]["situation"]
                progress = int(self.cli.array_data[array_name]["rebuilding_progress"])
                state = self.cli.array_data[array_name]["state"]

                if situation == "REBUILDING" and progress < rebuild_progress:
                    logger.info(
                        f"{array_name} REBUILDING in Progress... [{progress}%]"
                    )
                elif situation == "REBUILDING":
                    logger.info(
                        f"{array_name} REBUILDING completed [{rebuild_progress}%]"
                    )
                    return False
                else:
                    logger.info(f"{array_name} REBUILDING is Stoped/Not Started!")
                    logger.info(f"Situation: {situation}, State: {state}")
                    return False
            else:
                logger.error(f" {array_name}  Info command failed.")
                return False
        except Exception as e:
            logger.error("Command execution failed with exception {}".format(e))
            return False
        return True

    def array_rebuild_wait(
        self, array_name: str = None, wait_time: int = 5, loop_count: int = 20, rebuild_percent=100
    ) -> bool:
        """
        Method to check rebuild status
        Args:
            array_name (str) "name of the array" (optional)
        Returns:
            bool
        """
        try:
            if array_name == None:
                array_name = self.array
            counter = 0
            while counter <= loop_count:
                if not self.check_rebuild_status(array_name, 
                                                 rebuild_progress=rebuild_percent):
                    # The rebuild is not in progress
                    break
                time.sleep(wait_time)

            if counter > loop_count:
                if not self.check_rebuild_status(array_name,
                                                 rebuild_progress=rebuild_percent):
                    logger.info(f"Rebuilding wait time completed... {array_name}")
                    return False
            else:
                logger.info(f"Rebuilding completed for the array {array_name}")

            # Increment the counter
            counter += 1
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False
        return True

    def array_rebuild_wait_multiple(
        self, array_list: list, wait_time: int = 5, loop_count: int = 20
    ) -> bool:
        """
        Method to check rebuild status of multiple array
        Args:
            array_list (list):  List of name of the arrays
        Returns:
            bool
        """
        try:
            counter = 0
            rebuild_complete_array = []
            while counter <= loop_count:
                for array_name in array_list:
                    if not self.check_rebuild_status(array_name):
                        array_list.remove(array_name)
                        rebuild_complete_array.append(array_name)
                        # The rebuild is not in progress
                if not array_list:
                    break
                time.sleep(wait_time)

            if counter > loop_count:
                res = True
                for array_name in array_list:
                    if not self.check_rebuild_status(array_name):
                        logger.info(f"Rebuilding wait time completed... {array_name}")
                        res = False
                if not res:
                    return False
            else:
                logger.info(f"Rebuilding completed for the arrays {rebuild_complete_array}")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False
        return True

    def create_volume_multiple(self, array_name: str, num_vol: int, 
                               vol_name: str = "PoS_VoL", bw: int = 0,
                               maxiops: int = 0, size: str = "100GB") -> bool:
        """
        method to create_multiple_volumes
        Args:
            array_name (str) :name of the array
            num_vol (int) number of volumes to be created
            vol_name (str) : name of the volume to be created
            size (str) : size in GB/TB
            maxiops (int) : max iops supported
            bw (int) : bandwidth of volume
            #TODO add support for other QOS params
        Returns:
            bool
        """
        try:
            if size == None or size == "None":
                assert self.cli.array_info(array_name)[0] == True
                temp = self.helper.convert_size(
                    int(self.cli.array_data[array_name]["size"])
                )
                if "TB" in temp:
                    size_params = int(float(temp[0]) * 1000)
                    size_per_vol = int(size_params / num_vol)
                    d_size = str(size_per_vol) + "GB"
            else:
                d_size = size
            for i in range(num_vol):
                volume_name = f"{array_name}_{vol_name}_{str(i)}"
                assert (
                    self.cli.volume_create(
                        volume_name, d_size, array_name, iops=maxiops, bw=bw
                    )[0]
                    == True
                )
        except Exception as e:
            logger.error(f"Create volume '{volume_name}' failed due to {e}")
            return False
        return True

    def mount_volume_multiple(self, array_name: str,
                              volume_list: list, nqn: str) -> bool:
        """
        mount volumes to the SS
        Args:
            array_name (str) : name of the array
            volume_list (list) : list of the volumes to be mounted
            nqn : subsystems to be mounted
        Returns:
            bool
        """

        try:
            for vol in volume_list:
                assert self.cli.volume_mount(volumename=vol, 
                                             array_name=array_name, 
                                             nqn=nqn)[0] == True
        except Exception as e:
            logger.error(f"Mount volume'{vol}' failed due to {e}")
            return False
        return True

    def create_subsystems_multiple(
        self,
        ss_count: int,
        base_name: str,
        ns_count: int = 512,
        serial_number: str = "POS000000000001",
        model_number: str = "POS_VOLUME",
    ) -> bool:
        """
        Method to create more than one SS
        Args:
            ss_count (int) : Number of SS to be created
            base_name (str) : Subsystem Base Name
            ns_count (int) : Number of NS can be supported
            serial_number (str) : Serial number of subsystem
            model_number (str) : Model number of subsystem
        Returns:
            bool
        """
        try:
            for i in range(ss_count):
                if base_name:
                    ss_name = self.generate_nqn_name(default_nqn_name=base_name)
                else:
                    ss_name = self.generate_nqn_name()
                assert (
                    self.cli.subsystem_create(
                        ss_name, ns_count, serial_number, model_number
                    )[0]
                    == True
                )
            return True
        except Exception as e:
            logger.error(f"Subsystem creation failed due to {e}")
            return False

    def get_subsystems_list(self) -> bool:
        """
        method to list all the avaliable SS and pop dicovery subsystem
        ss_temp_list (class varaible) | (list) : has the list of subsystems created
        Returns :
            bool
        """
        try:
            assert self.cli.subsystem_list()[0] == True
            self.ss_temp_list = list(self.cli.nvmf_subsystem.keys())
            self.ss_temp_list.remove("nqn.2014-08.org.nvmexpress.discovery")
            subsystem_data = {}
            for ss_nqn in self.ss_temp_list:
                ss_data = self.cli.nvmf_subsystem[ss_nqn]
                subsystem_data[ss_nqn] = {}
                subsystem_data[ss_nqn]["nqn_name"] = ss_data["nqn"]
                subsystem_data[ss_nqn]["ns_count"] = ss_data["maxNamespaces"]
                subsystem_data[ss_nqn]["model_number"] = ss_data["modelNumber"]
                subsystem_data[ss_nqn]["serial_number"] = ss_data["serialNumber"]
                subsystem_data[ss_nqn]["transport"] = []
                subsystem_listner_list = ss_data.get("listenAddresses", [])
                for listner in subsystem_listner_list:
                    listner_data = {}
                    listner_data["transport_type"] = listner["transportType"]
                    listner_data["transport_port"] = listner["transportServiceId"]
                    listner_data["transport_ip"] = listner["targetAddress"]
                    subsystem_data[ss_nqn]["transport"].append(listner_data) 
            self.subsystem_data = subsystem_data
            logger.debug(f"{self.subsystem_data}")
            return True
        except Exception as e:
            logger.error(f"subsystem list failed due to {e}")
            return False

    def get_disk_info(self) -> bool:
        """
        method to get all info about all SSDs connected
        disk_info (class variable) | (dict) : has info regarding System and array disks
        Returns:
            bool
        """
        try:
            assert self.cli.device_list()[0] == True
            assert self.cli.array_list()[0] == True
            array_list = list(self.cli.array_dict.keys())
            self.mbr_dict = {}
            if len(array_list) == 0:
                logger.info("No Array found in the System")
                return False

            for array in list(self.cli.array_dict.keys()):
                self.cli.array_info(array_name=array)[0] == True
                self.mbr_dict[array] = [
                    self.cli.array_data[array]["data_list"],
                    [self.cli.array_data[array]["spare_list"]],
                ]
                self.mbr_dict[array] = [
                    disk for sublist in self.mbr_dict[array] for disk in sublist
                ]

            self.disk_info = {
                "system_disks": self.cli.system_disks,
                "mbr_disks": self.mbr_dict,
            }
            return True

        except Exception as e:
            logger.error(e)
            return False

    def bringup_system(self, data_dict: dict) -> bool:
        """method to bringup system phase"""
        ##TODO set pos path
        #self.setup_core_dump()
        #self.setup_max_map_count()
        #self.udev_install()
        
        self.static_dict = data_dict
        ###system config
        if self.static_dict["system"]["phase"] == "true":
            assert self.cli.pos_start()[0] == True
            assert self.cli.subsystem_create_transport()[0] == True
        return True

    def bringup_device(self, data_dict: dict) -> bool:
        """method to bringup device"""
        self.static_dict = data_dict
        if self.static_dict["device"]["phase"] == "true":
            device_list = self.static_dict["device"]["uram"]
            for uram in device_list:
                assert (
                    self.cli.device_create(
                        uram_name=uram["uram_name"],
                        bufer_size=uram["bufer_size"],
                        strip_size=uram["strip_size"],
                        numa=uram["numa_node"],
                    )[0]
                    == True
                )

            assert self.cli.device_scan()[0] == True
            assert self.cli.device_list()[0] == True
        return True

    def bringup_subsystem(self, data_dict: dict) -> bool:
        """method to bringup subsystem"""
        try:
            self.static_dict = data_dict
            if self.static_dict["subsystem"]["phase"] == "true":
                ss = self.static_dict["subsystem"]
                for ssinfo in ss["pos_subsystems"]:
                    assert (
                        self.create_subsystems_multiple(
                            ssinfo["nr_subsystems"],
                            base_name=ssinfo["base_nqn_name"],
                            ns_count=ssinfo["ns_count"],
                            serial_number=ssinfo["serial_number"],
                            model_number=ssinfo["model_name"],
                        )
                        == True
                    )

                assert self.get_subsystems_list() == True

                for subsystem in self.ss_temp_list:
                    assert (
                        self.cli.subsystem_add_listner(
                            subsystem, self.helper.ip_addr[0], "1158"
                        )[0]
                        == True
                    )
            return True
        except Exception as e:
            logger.error(f"Subsystem bringup failed due to {e}")
            traceback.print_exc()
            return False

    def bringup_array(self, data_dict: dict) -> bool:
        """method to bringup array"""
        try:
            self.static_dict = data_dict
            if self.static_dict["array"]["phase"] == "true":
                assert self.cli.devel_resetmbr()[0] == True
                assert self.cli.device_list()[0] == True
                system_disks = self.cli.system_disks

                pos_array_list = self.static_dict["array"]["pos_array"]
                nr_pos_array = self.static_dict["array"]["num_array"]
                if nr_pos_array != len(pos_array_list):
                    logger.info("JSON file data is inconsistent. POS bringup may fail")

                for array_index in range(nr_pos_array):
                    array = pos_array_list[array_index]
                    array_name = array["array_name"]
                    nr_data_drives = array["data_device"]
                    nr_spare_drives = array["spare_device"]

                    if len(system_disks) < (nr_data_drives + nr_spare_drives):
                        pytest.skip("Insufficient system disks {}. Required minimum {}".format(
                                len(system_disks), nr_data_drives + nr_spare_drives))

                    if array["auto_create"] == "false":
                        data_disk_list = [
                            system_disks.pop(0) for i in range(nr_data_drives)
                        ]
                        spare_disk_list = [
                            system_disks.pop(0) for i in range(nr_spare_drives)
                        ]
                        assert self.cli.array_create(array_name,
                                        write_buffer=array["uram"],
                                        data=data_disk_list,
                                        spare=spare_disk_list,
                                        raid_type=array["raid_type"])[0] == True
                    else:
                        assert self.cli.array_autocreate(array_name,
                                        array["uram"], nr_data_drives,
                                        raid_type=array["raid_type"],
                                        num_spare=nr_spare_drives)[0] == True

                        assert self.cli.array_info(array_name=array_name)[0] == True
                        d_dev = set(self.cli.array_data[array_name]["data_list"])
                        s_dev = set(self.cli.array_data[array_name]["spare_list"])
                        system_disks = list(set(system_disks) - d_dev.union(s_dev))

                    if array["mount"] == "true":
                        write_back = True
                        if array["write_back"] == "false":
                            write_back = False
                        assert (
                            self.cli.array_mount(
                                array_name=array_name, write_back=write_back
                            )[0]
                            == True
                        )
        except Exception as e:
            logger.error("POS bring up failed due to {}".format(e))
            return False
        return True

    def bringup_volume(self, data_dict: dict) -> bool:
        try:
            self.static_dict = data_dict
            if self.static_dict["volume"]["phase"] == "true":
                logger.info(f"volume data dict : {data_dict['volume']['pos_volumes']}")
                assert self.cli.array_list()[0] == True
                if len(list(self.cli.array_dict.keys())) == 2:
                    volumes = self.static_dict["volume"]["pos_volumes"]
                else:
                    volumes = [self.static_dict["volume"]["pos_volumes"][0]]
                for vol in volumes:
                    array_name = vol["array_name"]
                    assert self.cli.volume_list(array_name)
                    old_vols = self.cli.vols
                    assert self.create_volume_multiple(array_name, 
                            vol["num_vol"], vol_name=vol["vol_name_pre"],
                            size=vol["size"], bw=vol["qos"]["maxbw"],
                               maxiops=vol["qos"]["maxiops"]) == True

                    if vol["mount"]["phase"]:
                        assert self.cli.volume_list(array_name)[0] == True
                        assert self.get_subsystems_list() == True
                        subsystem_range = vol["mount"]["subsystem_range"]

                        numss, numvol = map(int, subsystem_range.split("-"))
                        ss_list = self.ss_temp_list
                        nqn_list = [nqn for nqn in ss_list if array_name in nqn]
                        logger.info(f"Number of volumes per Subsystem {str(numvol)}")
                        if len(nqn_list) == 1:
                            assert self.mount_volume_multiple(
                                                array_name=array_name,
                                                volume_list=self.cli.vols,
                                                nqn=nqn_list[0]) == True
                        else:
                            mountcount = 0
                            nqn_index = 0
                            while mountcount < len(self.cli.vols):
                                nqnname = nqn_list[nqn_index]
                                volname = self.cli.vols[mountcount]
                                assert self.cli.volume_mount(volumename=volname,
                                                        array_name=array_name,
                                                        nqn=nqnname)[0] == True
                                mountcount += 1
                                if mountcount % numvol == 0:
                                    nqn_index += 1
        except Exception as e:
            logger.error("POS bring up failed due to {}".format(e))
            return False
        return True


    def pos_bring_up(self, data_dict: dict = None) -> bool:
        """
        method to perform the pos_bringup_sequence ../testcase/config_files/pos_config.json
        Returns:
            bool
        """
        try:
            if data_dict:
                self.static_dict = data_dict
            logger.info(self.static_dict)

            assert self.bringup_system(data_dict=self.static_dict) == True
            assert self.bringup_device(data_dict=self.static_dict) == True
            assert self.bringup_subsystem(data_dict=self.static_dict) == True
            assert self.bringup_array(data_dict=self.static_dict) == True
            assert self.bringup_volume(data_dict=self.static_dict) == True

            return True
        except Exception as e:
            logger.error("POS bring up failed due to {}".format(e))
            return False

    def setup_env_pos(
        self,
        hugepages: str = "7000",
        rd_nr: str = "2",
        rd_size: str = "4194304",
        max_part: str = "0",
        driver_load: bool = False,
    ) -> bool:
        """
        Method : runs Setup_sh scripts in SPDK
        Args:
            hugepages : Num Hugepages
            SPDK_version SPDK version
            rd_nr = rd_nr value to load driver
            rd_size : rd size to load driver
            max_part : maz part to load driver
            driver_load : Default false
        Returns:
            bool

        """
        try:
            if driver_load == True:
                driver_load_cmd = "modprobe brd rd_nr=%s rd_size=%s max_part=%s" % (
                    rd_nr,
                    rd_size,
                    max_part,
                )
                out = self.ssh_obj.execute(driver_load_cmd)
                if not out:
                    logger.error("Failed to execute '%s'" % driver_load_cmd)
                    return False

            drop_caches_cmd = "echo 3 > /proc/sys/vm/drop_caches"
            self.ssh_obj.execute(drop_caches_cmd)

            setup_env_cmd = (
                self.cli.pos_path + "/lib/spdk/scripts" + "/setup.sh" + " reset"
            )
            out = self.ssh_obj.execute(setup_env_cmd)
            if not out:
                logger.error("Failed to execute '{}'".format(setup_env_cmd))
                return False
            else:
                out_cmd = "".join(out)

            huge_page_cmd = "sudo HUGE_EVEN_ALLOC=yes NRHUGE=%s %s" % (
                hugepages,
                self.cli.pos_path + "/lib/spdk/scripts" + "/setup.sh",
            )
            out = self.ssh_obj.execute(huge_page_cmd)
            if not out:
                logger.error("Failed to execute '%s'" % huge_page_cmd)
                return False
            else:
                out_cmd = "".join(out)
                logger.info(out_cmd)

            assert self.setup_core_dump() == True
            assert self.setup_max_map_count() == True
            assert self.udev_install() == True
            assert self.check_udev_rule()
            return True
        except Exception as e:
            logger.error("Execution  failed because of {}".format(e))
            return False

    def setup_core_dump(self) -> bool:
        """
        method to setup core dump
        Returns:
            bool
        """
        try:

            logger.info("set core size to unlimit")
            cmd = "ulimit -c unlimited"
            assert self.run_shell_command(cmd) == True
            logger.info("disable apport service")
            cmd = "systemctl disable apport.service"
            assert self.run_shell_command(cmd) == True
            cmd = "mkdir -p /etc/pos/core"
            assert self.run_shell_command(cmd) == True
            cmd = 'echo "/etc/pos/core/%E.core" > /proc/sys/kernel/core_pattern'
            assert self.run_shell_command(cmd) == True
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def setup_max_map_count(self) -> bool:
        """
        method to set max map count
        Returns:
            bool
        """
        try:

            max_map_count = 65535
            cmd = "echo 3 > /proc/sys/vm/drop_caches"
            assert self.run_shell_command(cmd) == True
            cmd = "cat /proc/sys/vm/max_map_count"
            assert self.run_shell_command(cmd) == True
            current_max_map_count = int("".join(self.shell_out))
            log_msg = "maximum # of memory map areas per process"
            logger.info(f"Current {log_msg} is {current_max_map_count}")
            if current_max_map_count < max_map_count:
                logger.info(f"Setting {log_msg} to {max_map_count}")
                cmd = f"sudo sysctl -w vm.max_map_count={max_map_count}"
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def run_shell_command(self, command: str, 
                          expected_exit_code: int = 0) -> bool:
        """
        Method to run shell commands
        Args:
            command (str) : command to be executed
            expected_exit_code (int) : exit_code
        Returns:
            bool
        """
        try:
            out = self.ssh_obj.execute(command=command,
                                       expected_exit_code=expected_exit_code)

            self.shell_out = out
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def get_dir_list(self, dir_path: str) -> (bool, list):
        """
        method to get file content using cat command
        """
        try:
            cmd = "ls {}".format(dir_path)
            out = self.run_shell_command(cmd)
            content = None
            if out is True:
                content = self.shell_out
            return out, content
        except Exception as e:
            logger.error(f"Command Execution failed due to {e}")
            return False

    def get_file_content(self, file_path: str) -> bool:
        """
        method to get file content using cat command
        """
        try:
            cmd = "cat {}".format(file_path)
            out = self.run_shell_command(cmd)
            content = None
            if out is True:
                content = self.shell_out
            return out, content
        except Exception as e:
            logger.error(f"Command Execution failed due to {e}")
            return False

    def check_udev_rule(self) -> bool:
        """
        Method to check if the udev rule is applied
        Returns:
            bool

        """
        udev_file_path = "/etc/udev/rules.d/99-custom-nvme.rules"
        udev_dir = "/".join(udev_file_path.split("/")[:-1])
        udev_file_name = udev_file_path.split("/")[-1]
        out, content = self.get_dir_list(dir_path=udev_dir)
        if out is True:
            if udev_file_name in " ".join(content):
                self.udev_rule = True
                logger.info("The udev rule is applied")
            else:
                self.udev_rule = False
                logger.info("The udev rule is not applied")
                
        return True

    def get_pos(self) -> bool:
        """
        method to dump all the get commmands o/p from POS CLI
        Returns:
            bool
        """
        logger.info("======================= SYSTEM =========================")
        assert self.cli.system_info()[0] == True
        logger.info("======================= ARRAY ==========================")

        assert self.cli.array_list()[0] == True

        array_list = list(self.cli.array_dict.keys())
        for array in array_list:
            assert self.cli.array_info(array_name=array)[0] == True

        logger.info("======================= VOLUME =========================")
        for array in array_list:
            assert self.cli.volume_list(array_name=array)[0] == True

        logger.info("======================= DEVICE==========================")
        assert self.cli.device_list()[0] == True
        logger.info("======================= QOS ============================")
        for array in array_list:
            assert self.cli.volume_list(array_name=array)[0] == True
            for vol in self.cli.vols:
                assert self.cli.qos_list_volume_policy(volumename=vol,
                                           arrayname=array)[0] == True

        logger.info("======================= LOGGER==========================")
        assert self.cli.logger_info()[0] == True

        logger.info("======================= SUBSYSTEM ======================")
        assert self.cli.subsystem_list()[0] == True
        return True

    def _por_backup(self):
        try:
            logger.info("Store system information before Poweroff")
            self.backup_data = {}
            self.backup_data["buffer_dev"] = {}
            assert self.cli.device_list()[0] == True
            for uram_name in self.cli.dev_type["NVRAM"]:
                buffer_dev = self.cli.device_map[uram_name]
                logger.info(f"{buffer_dev}")
                self.backup_data["buffer_dev"][uram_name] = buffer_dev

            assert self.cli.transport_list()[0] == True
            self.backup_data["transport_list"] = self.cli.transports

            assert self.get_subsystems_list() == True
            self.backup_data["subsystem"] = copy.deepcopy(self.subsystem_data)

            logger.debug(f"{self.backup_data['subsystem']}")
            self.backup_data["mounted_array"] = []
            self.backup_data["mounted_vol"] = []

            res, jout = self.cli.array_list()
            assert res == True
            array_list = jout["result"]["data"]["arrayList"]
            for array in array_list:
                if array["status"].lower() == "mounted":
                    # Store mounted arrays info to mount it back after SPOR
                    array_data = {}
                    arr_name = array["name"]
                    array_data["array_name"] = arr_name
                    array_data["wt_enabled"] = array["writeThroughEnabled"]

                    self.backup_data["mounted_array"].append(array_data)

                    assert self.cli.volume_list(array_name=arr_name)[0] == True
                    for vol in self.cli.vols:
                        vol_status = self.cli.vol_dict[vol]["status"].lower()
                        if vol_status == "mounted":
                            assert self.cli.volume_info(array_name=arr_name, 
                                                        vol_name=vol)[0] == True

                            # Store mounted volume info to mount it back after SPOR
                            volume = self.cli.volume_data[arr_name][vol]
                            volume_data = {}
                            volume_data["volume_name"] = volume["name"]
                            volume_data["array_name"] = volume["array_name"]
                            volume_data["nqn_name"] = volume["subnqn"]

                            self.backup_data["mounted_vol"].append(volume_data)
            return True
        except Exception as e:
            logger.error(f"Failed to do backup before POR due to {e}")
            return False

    def _por_prep(self, wbt_flush: bool,
                  uram_backup: bool, grace_shutdown: bool) -> bool:
        """
        Method to por preparation
        wbt_flush : If true, Issue the wbt flush command
        uram_backup : If true, run script to take uram backup

        Returns:
            bool
        """
        try:
            if wbt_flush:
                assert self.cli.wbt_flush()[0] == True

            assert self.cli.pos_stop(grace_shutdown=grace_shutdown)[0] == True

            if uram_backup:
                self.helper.get_pos_path()
                path = self.helper.pos_path
                cmd = f"{path}/script/backup_latest_hugepages_for_uram.sh"
                self.ssh_obj.execute(cmd, get_pty=True)

            return True
        except Exception as e:
            logger.error(f"Failed to do POR preparation due to {e}")
            return False

    def _do_por(self, por_type: str = 'spor', pos_as_service = True,
                wbt_flush: bool = False, force_uram_backup: bool = False):
        try:
            graceful_stop = False
            write_back_array = False
            uram_backup = False

            if por_type == 'npor':
                for volume in self.backup_data["mounted_vol"]:
                    vol_name = volume["volume_name"]
                    arr_name = volume["array_name"]
                    assert self.cli.volume_unmount(volumename=vol_name,
                                            array_name=arr_name)[0] == True

                for array_data in self.backup_data["mounted_array"]:
                    array_name = array_data["array_name"]
                    if not array_data["wt_enabled"]:
                        uram_backup = True
                    assert self.cli.array_unmount(array_name)[0] == True

                graceful_stop = True

            if force_uram_backup and not pos_as_service:
                uram_backup = True

            assert self._por_prep(wbt_flush=wbt_flush, uram_backup=uram_backup,
                                  grace_shutdown=graceful_stop) == True

            return True
        except Exception as e:
            logger.error(f"Failed to do POR due to {e}")
            return False

    def _por_bringup(self, force_uram_backup: bool = False):
        try:
            logger.info("Restore system after Power-on")
            # Start The POS system
            assert self.cli.pos_start()[0] == True

            # Create the URAM device
            for uram, uram_data in self.backup_data["buffer_dev"].items():
                assert self.cli.device_create(uram_name=uram)[0] == True

            assert self.cli.device_scan()[0] == True

            # Create subsystem and Add listner
            assert self.cli.subsystem_create_transport()[0] == True

            logger.info(f"{self.backup_data}")
            subsystems = self.backup_data["subsystem"]
            logger.info(f"{subsystems}")
            for ss_nqn, subsystem_data in subsystems.items():
                ns_count = subsystem_data["ns_count"]
                model = subsystem_data["model_number"]
                serial = subsystem_data["serial_number"]
                assert self.cli.subsystem_create(ss_nqn, ns_count=ns_count,
                        serial_number=serial, model_name=model)[0] == True
                
                for listner_data in subsystem_data["transport"]:
                    transport = listner_data["transport_type"]
                    port = listner_data["transport_port"]
                    ip_addr = listner_data["transport_ip"]

                    assert self.cli.subsystem_add_listner(nqn_name=ss_nqn,
                            mellanox_interface=ip_addr, port=port)[0] == True
            return True
        except Exception as e:
            logger.error(f"Failed to do POR due to {e}")
            return False

    def verify_buffer_dev(self):
        try:
            assert self.cli.device_list()[0] == True
            err_list = []
            dev_list = []
            for uram_name in self.backup_data["buffer_dev"].keys():
                logger.info(f"Buffer Dev : {uram_name}")
                if (uram_name not in self.cli.system_buffer_devs 
                    and uram_name not in self.cli.array_buffer_devs):
                    err_list.append(uram_name)
                else:
                    dev_list.append(uram_name)

            if dev_list:
                logger.info(f"Buffer devices {dev_list} is created")

            if err_list:
                logger.error(f"Buffer devices {err_list} is not created")
                return False

            logger.info(f"Buffer dev varification after auto recovery completed")
            return True
        except Exception as e:
            logger.error(f"Buffer dev varification after auto recovery failed due to {e}")
            return False

    def verify_subsystems(self):
        try:
            assert self.get_subsystems_list() == True

            for ss_name, ss_data in self.backup_data["subsystem"].items():
                assert ss_name in self.subsystem_data.keys()
                nvmf_ss = self.subsystem_data[ss_name]
                assert ss_data["nqn_name"] ==  nvmf_ss["nqn_name"]
                assert ss_data["ns_count"] == nvmf_ss["ns_count"]
                assert ss_data["model_number"] == nvmf_ss["model_number"]
                assert ss_data["serial_number"] == nvmf_ss["serial_number"]

                nvmf_ss_listener = nvmf_ss.get("transport", [])
                assert len(ss_data["transport"]) == len(nvmf_ss_listener)

            logger.info(f"subsystem varification after auto recovery completed")
            return True
        except Exception as e:
            logger.error(f"subsystem varification after auto recovery failed due to {e}")
            return False     

    def por_recovery(self, restore_verify=True, wait_time=120):
        try:
            logger.info("Verify system auto recovery after Power-on")
            # Start The POS system
            assert self.cli.pos_start()[0] == True

            logger.info(f"Wait {wait_time} seconds after pos start")
            time.sleep(wait_time)

            if restore_verify:
                # Verify the URAM device
                assert self.verify_buffer_dev() == True

                # Verify the Transport and subsystem
                assert self.cli.transport_list()[0] == True
                self.backup_data["transport_list"] = self.cli.transport_list

                # Verify subsystem and listeners
                assert self.verify_subsystems() == True
            
                logger.info(f"Varification after auto recovery completed")

            logger.info(f"POR recovery completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to do POR auto recovery due to {e}")
            return False

    def _por_mount_array_volume(self):
        try:
            mounted_arrays = self.backup_data["mounted_array"]
            # Restore Array and Volumes
            for array_data in mounted_arrays:
                array_name = array_data["array_name"] 
                write_back = not array_data["wt_enabled"]
                assert self.cli.array_mount(array_name=array_name,
                                            write_back=write_back)[0] == True

            mounted_volumes = self.backup_data["mounted_vol"]
            for volume_data in mounted_volumes:
                array_name = volume_data["array_name"]
                volume_name = volume_data["volume_name"]
                nqn_name = volume_data["nqn_name"]

                assert self.cli.volume_mount(volumename=volume_name,
                                             array_name=array_name,
                                             nqn=nqn_name)[0] == True
            return True
        except Exception as e:
            logger.error(f"Failed to mount array and volume due to {e}")
            return False

    def npor(self, mount_post_npor: bool = True, 
             save_restore=False, restore_verify=True) -> bool:
        """
        Method to perform NPOR
        Returns:
            bool
        """
        try:
            logger.info("Start NPOR operation...")
            assert self._por_backup() == True
            assert self._do_por(por_type = 'npor') == True
            if save_restore:
                assert self.por_recovery(restore_verify=restore_verify) == True
            else:
                assert self._por_bringup() == True
                if mount_post_npor: 
                    assert self._por_mount_array_volume() == True
            return True
            logger.info("NPOR operation completed successfully.")
        except Exception as e:
            logger.error(f"NPOR failed due to {e}")
            traceback.print_exc()
            return False

    def spor(self, uram_backup: bool = False, pos_as_service = None,
            write_through: bool = False, mount_post_npor: bool = True,
            save_restore=False, restore_verify=True) -> bool:
        """
        Method to spor
        uram_backup : If true, run script to take uram backup

        Returns:
            bool
        """
        try:
            logger.info("Start SPOR operation...")
            if pos_as_service == None:
                pos_as_service = self.pos_as_service

            assert self._por_backup() == True
            assert self._do_por(por_type = 'spor', 
                                pos_as_service=pos_as_service,
                                force_uram_backup=uram_backup) == True
            if save_restore:
                assert self.por_recovery(restore_verify=restore_verify) == True
            else:
                assert self._por_bringup() == True
                if mount_post_npor: 
                    assert self._por_mount_array_volume() == True

            logger.info("SPOR operation completed successfully.")
            return True
        except Exception as e:
            logger.error(f"SPOR failed due to {e}")
            traceback.print_exc()
            return False

    def reboot_with_backup(self, save_restore=False, restore_verify=True):
        '''Method to reboot and bring up ther arrays and volumes'''
        try:
            assert self._por_backup() == True
            assert self.reboot_and_reconnect() == True
            if save_restore:
                assert self.por_recovery(restore_verify=restore_verify) == True
            else:
                assert self._por_bringup() == True
                assert self._por_mount_array_volume() == True
            return True
        except Exception as e:
            logger.error(f"SPOR failed due to {e}")
            traceback.print_exc()
            return False

    def delete_all_volumes(self, arrayname):
        """method to delete all volumes if any in a given array"""
        try:
            assert self.cli.array_list()[0] == True
            if arrayname in list(self.cli.array_dict.keys()):
                assert self.cli.volume_list(array_name=arrayname)[0] == True
                if len(self.cli.vols) == 0:
                    logger.info("No volumes found")

                for vol in self.cli.vols:
                    assert self.cli.volume_info(array_name=arrayname,
                                                vol_name=vol)[0] == True
                    vol_status = self.cli.volume_data[arrayname][vol]["status"]
                    if vol_status.lower() == "mounted":
                        assert self.cli.volume_unmount(volumename=vol,
                                            array_name=arrayname)[0] == True

                    assert self.cli.volume_delete(volumename=vol, 
                                            array_name=arrayname)[0] == True
            return True
        except Exception as e:
            logger.error(e)
            return False

    def reboot_and_reconnect(self):
        '''Method to reboot the machine'''
        out = self.ssh_obj.execute("reboot")
        logger.info("Reboot initiated")
        assert self.ssh_obj.reconnect_after_reboot() == True
        return True

    def report_log_array(self,progress,completion = '100'):
        '''Method to get the latest updates in report.log'''
        try:
            #verify report.log present in /var/log/pos path
            path_cmd = 'ls -ltr /var/log/pos | grep report.log'
            path_out = self.ssh_obj.execute(path_cmd)
            if path_out:
                #verify array mount command progress in report.log
                if progress == "array_mount":
                    mnt_cmd = f"tail -n 10 /var/log/pos/report.log | grep -F 'ARRAY_MOUNT_PROGRESS, {[completion]}'"
                    mnt_out = self.ssh_obj.execute(mnt_cmd)
                    if not mnt_out:
                        logger.error("Failed to execute '{}'".format(mnt_cmd))
                        return False
                    else:
                        out_mnt_cmd = "".join(mnt_out)
                        return out_mnt_cmd
                #verify array unmount command progress in report.log
                elif progress == "array_unmount":
                    unmnt_cmd = f"tail -n 10 /var/log/pos/report.log | grep -F 'ARRAY_UNMOUNT_PROGRESS, {[completion]}'"
                    unmnt_out = self.ssh_obj.execute(unmnt_cmd)
                    if not unmnt_out:
                        logger.error("Failed to execute '{}'".format(unmnt_cmd))
                        return False
                    else:
                        out_unmnt_cmd = "".join(unmnt_out)
                        return out_unmnt_cmd
        except Exception as e:
            logger.error(e)
            return False

    def report_log_volume(self,progress,completion = '6/6'):
        '''Method to get the latest updates in report.log'''
        try:
            #verify report.log present in /var/log/pos path
            path_cmd = 'ls -ltr /var/log/pos | grep report.log'
            path_out = self.ssh_obj.execute(path_cmd)
            if path_out:
                #verify volume mount command progress in report.log
                if progress == "volume_mount":
                    vol_mnt_cmd = f"tail -n 10 /var/log/pos/report.log | grep -F 'Mount Sequence In Progress({completion})'"
                    vol_mnt_out = self.ssh_obj.execute(vol_mnt_cmd)
                    if not vol_mnt_out:
                        logger.error("Failed to execute '{}'".format(vol_mnt_cmd))
                        return False
                    else:
                        out_vol_mnt_cmd = "".join(vol_mnt_out)
                        return out_vol_mnt_cmd
                #verify volume unmount command progress in report.log
                elif progress == "volume_unmount":
                    vol_unmnt_cmd = f"tail -n 10 /var/log/pos/report.log | grep -F 'Unmount Sequence In Progress({completion})'"
                    vol_unmnt_out = self.ssh_obj.execute(vol_unmnt_cmd)
                    if not vol_unmnt_out:
                        logger.error("Failed to execute '{}'".format(vol_unmnt_cmd))
                        return False
                    else:
                        out_vol_unmnt_cmd = "".join(vol_unmnt_out)
                        return out_vol_unmnt_cmd
        except Exception as e:
            logger.error(e)
            return False

    ##TODO update pos path
    def dump_core(self):
        """
        Method to collect core dump by giving different options depending on
        whether poseidonos is running or already creashed.
        """
        try:
            if self.helper.check_pos_exit() == False:
                out = self.ssh_obj.execute("pkill -11 poseidonos")
              
            if not self.pos_as_service:
                self.cli_path = self.helper.get_pos_path()
            else:
                self.cli_path = "/usr/local/bin"
            command = "{}/tool/dump/trigger_core_dump.sh crashed".format(
                  self.cli_path )
              
            out = self.ssh_obj.execute(command)
            logger.info("core dump file created: {}".format(out))
           
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def copy_core(self, unique_key, dir="/root"):
        """
        Method to rename the core dump file using unique key and issue key
        """
        try:
            core_files_dir = "/etc/pos/core/"

            # Zip all core files
            cmd = f"zip -r {dir}/core_{unique_key}.zip {core_files_dir}"
            out = self.ssh_obj.execute(cmd)
            if type(out) == list:
                out = " ".join(out)
                if "zip: command not found" in out:
                    logger.warning("ZIP is not installed in system. Skipped core copy")
                else:
                    logger.info(f"Copied core dump file {out}.")
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False
    
    def copy_pos_log(self, unique_key, dir="/root"):
        """
        Method to rename the core dump file using unique key and issue key
        """
        try:
            pos_log_dir = "/var/log/pos/"

            # Zip all log files
            cmd = f"zip -r {dir}/logs_{unique_key}.zip {pos_log_dir}"

            out = self.ssh_obj.execute(cmd)
            if type(out) == list:
                out = " ".join(out)
                if "zip: command not found" in out:
                    logger.warning("ZIP is not installed in system. Skipped logs copy")
                else:
                    logger.info(f"POS log files copied {out}.")
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def remove_restore_file(self, file="/etc/pos/restore.json"):
        """
        Method to remove the restore json file
        """
        try:
            # Zip all core files
            logger.info("Remove old restore.json if any")
            cmd = f"rm -f {file}"
            out = self.ssh_obj.execute(cmd)
            logger.info(f"Removed file {file} {out}.")
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False
