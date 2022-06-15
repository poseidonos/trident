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
import re
import helper
import logger
from cli import Cli

logger = logger.get_logger(__name__)


class TargetUtils:
    """
    The Class objects will contain supporting methods to configure POS
    Args:
        ssh_obj : ssh obj of the Target
        data_dict (dict) : path for POS config
        pos_path : path of pos source
        array_name (str) : name of the POS array | (default = POS_ARRAY1)

    """

    def __init__(self, ssh_obj, data_dict: dict, pos_path: str):
        self.ssh_obj = ssh_obj
        self.static_dict = data_dict
        self.cli = Cli(ssh_obj, self.static_dict, pos_path)
        #self.array = array_name
        self.helper = helper.Helper(ssh_obj)
        self.udev_rule = False
        self.total_required = 0

    def generate_nqn_name(self, default_nqn_name: str = "nqn.2022-10.pos") -> str:
        """
        Method to generate nqn name
        Args:
            default_nqn_name (str) : name of the subsystem
        Returns:
            str
        """
        out = self.cli.list_subsystem()
        if out[0] is False:
            return None
        num = len(list(out[1].keys()))
        if num is 1:
            logger.info("creating first Nvmf Subsystem")
            return "{}:subsystem1".format(default_nqn_name)
        elif num is 0:
            logger.error("No Subsystem information found, please verify pos status")
            return None
        else:
            temp = list(out[1].keys())
            temp.remove("nqn.2014-08.org.nvmexpress.discovery")
            count = []
            for subsystem in temp:
                c = int(re.findall("[0-9]+", subsystem)[2])
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
            self.cli.list_device()
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
            self.cli.list_device()
            for each_dev in device_list:
                if each_dev not in self.cli.dev_type["SSD"]:
                    logger.error(
                        "given device {} is not connected to the system ".format(
                            each_dev
                        )
                    )
                    return False
            dev_map = self.dev_bdf_map()
            if dev_map[0] == False:
                logger.info("failed to get the device and bdf map")
                return False
            for dev in device_list:
                pci_addr = dev_map[1][dev]
                self.dev_addr.append(pci_addr)
                logger.info(
                    "pci address {} for the given device is {} ".format(pci_addr, dev)
                )
                hot_plug_cmd = "echo 1 > /sys/bus/pci/devices/{}/remove ".format(
                    pci_addr
                )
                logger.info("Executing hot plug command {} ".format(hot_plug_cmd))
                self.ssh_obj.execute(hot_plug_cmd)
                time.sleep(5)
                list_dev_out = self.dev_bdf_map()
                if list_dev_out[0] == False:
                    logger.error(
                        "failed to get the device and bdf map after removing the disk"
                    )
                    return False
                if pci_addr in list(list_dev_out[1].values()):
                    logger.warning(
                        "failed to hot plug the device {} verifing in list_device ".format(
                            dev
                        )
                    )
                    assert self.cli.list_device()[0] == True
                    if dev in self.cli.dev_type["SSD"]:
                        logger.error("failed to remove device")
                        return False
                else:
                    logger.info("Successfully removed the device {} ".format(dev))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False
        return True

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
                    logger.error(
                        "nvme device not found with the bdf {} ".format(
                            each_addr.strip()
                        )
                    )
                    return False
                logger.info("removing the bdf : {}".format(each_addr))
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

            re_scan_cmd = "echo 1 > /sys/bus/pci/rescan "
            self.ssh_obj.execute(re_scan_cmd)

            logger.info("scanning the devices after rescan")
            time.sleep(5)  # Adding 5 sec sleep for the sys to get back in normal state
            assert self.cli.scan_device()[0] == True

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

    def spor_prep(self) -> bool:
        """
        Method to spor preparation
        Returns:
            bool
        """
        try:
            assert self.cli.wbt_flush()[0] == True
            assert self.cli.stop_system()[0] == True
            self.ssh_obj.execute(
                "{}/script/backup_latest_hugepages_for_uram.sh".format(
                    self.cli.pos_path
                ),
                get_pty=True,
            )
            self.ssh_obj.execute("rm -fr /dev/shm/ibof*", get_pty=True)

        except Exception as e:
            logger.error(e)
            return False

    def check_rebuild_status(self, array_name: str = None) -> bool:
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

            if self.cli.info_array(array_name=array_name)[0]:
                situation = self.cli.array_info[array_name]["situation"]
                progress = self.cli.array_info[array_name]["rebuilding_progress"]
                state = self.cli.array_info[array_name]["state"]

                if situation == "REBUILDING":
                    logger.info(f"Array '{array_name}' REBUILDING in Progress... [{progress}%]")
                else:
                    logger.info(f"Array '{array_name}' REBUILDING is Stoped/Not Started!")
                    logger.info(f"Situation: {situation}, State: {state}")
                    return False
            else:
                logger.error(f"Array '{array_name}' Info command failed.")
                return False
        except Exception as e:
            logger.error("Command execution failed with exception {}".format(e))
            return False
        return True


    def array_rebuild_wait(self, array_name: str = None, wait_time: int = 5, loop_count: int = 20) -> bool:
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
                if not self.check_rebuild_status(array_name):
                    # The rebuild is not in progress
                    break
                time.sleep(wait_time)

            if counter > loop_count:
                if not self.check_rebuild_status(array_name):
                    logger.info(f"Rebuilding wait time completed... {array_name}")
                    return False
            else:
                logger.info(f"Rebuilding completed for the array {array_name}")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False
        return True

    def create_volume_multiple(
        self,
        array_name: str,
        num_vol: int,
        vol_name: str = "PoS_VoL",
        size: str = "100GB",
        maxiops: int = 100000,
        bw: int = 1000,
    ) -> bool:
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

        if size == None:
            assert self.cli.info_array(array_name)[0] == True
            temp = self.helper.convert_size(
                int(self.cli.array_info[array_name]["size"])
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
                self.cli.create_volume(
                    volume_name, d_size, array_name, iops=maxiops, bw=bw
                )[0]
                == True
            )
        return True

    def mount_volume_multiple(
        self, array_name: str, volume_list: list, nqn_list: list) -> bool:
        """
        mount volumes to the SS
        Args:
            array_name (str) : name of the array
            volume_list (list) : list of the volumes to be mounted
            nqn_list (list) : list of Subsystems to be mounted
        Returns:
            bool
        """
        num_ss = len(nqn_list)
        num_vol = len(volume_list)
        temp, num = 0, 0
        for num in range(num_vol):
            ss = nqn_list[temp] if len(nqn_list) > 1 else nqn_list[0]
            assert self.cli.mount_volume(volume_list[num], array_name, ss)[0] == True
            temp += 1
            if temp == num_ss - 1:
                temp = 0
        return True

    def create_subsystems_multiple(self, ss_count: int, base_name: str, 
                ns_count: int, serial_number: str, model_name: str) -> bool:
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
                assert self.cli.create_subsystem(ss_name, ns_count,
                                        serial_number, model_name)[0] == True
            return True
        except Exception as e:
            return False

    def get_subsystems_list(self) -> bool:
        """
        method to list all the avaliable SS and pop dicovery subsystem
        ss_temp_list (class varaible) | (list) : has the list of subsystems created
        Returns :
            bool
        """
        try:
            out = self.cli.list_subsystem()
            self.ss_temp_list = list(out[1].keys())
            self.ss_temp_list.remove("nqn.2014-08.org.nvmexpress.discovery")

            return True
        except Exception as e:
            logger.error(e)
            return False

    def get_disk_info(self) -> bool:
        """
        method to get all info about all SSDs connected
        disk_info (class variable) | (dict) : has info regarding System and array disks
        Returns:
            bool
        """
        try:
            assert self.cli.list_device()[0] == True
            assert self.cli.list_array()[0] == True
            array_list = list(self.cli.array_dict.keys())
            self.mbr_dict = {}
            if len(array_list) == 0:
                logger.info("No Array found in the System")
                return False

            for array in list(self.cli.array_dict.keys()):
                self.cli.info_array(array_name=array)[0] == True
                self.mbr_dict[array] = [
                    self.cli.array_info[array]["data_list"],
                    [self.cli.array_info[array]["spare_list"]],
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

    def pos_bring_up(self, data_dict: dict = None) -> bool:
        """
        method to perform the pos_bringup_sequence ../testcase/config_files/pos_config.json
        Returns:
            bool
        """
        try:
            if data_dict:
                self.static_dict = data_dict
            static_dict = self.static_dict
            assert self.helper.get_mellanox_interface_ip()[0] == True
            logger.info(self.static_dict)
            ###system config

            if static_dict["system"]["phase"] == "true":
                assert self.cli.start_system()[0] == True
                assert self.cli.create_transport_subsystem()[0] == True

            if static_dict["device"]["phase"] == "true":
                device_list = static_dict["device"]["uram"]
                for uram in device_list:
                    assert self.cli.create_device(uram_name = uram["uram_name"],
                                            bufer_size = uram["bufer_size"],
                                            strip_size = uram["strip_size"],
                                            numa = uram["numa_node"])[0] == True

                assert self.cli.scan_device()[0] == True

            if static_dict["subsystem"]["phase"] == "true":
                ss = static_dict["subsystem"]
                assert self.create_subsystems_multiple(ss["nr_subsystems"],
                                        base_name = ss["base_nqn_name"],
                                        ns_count = ss["ns_count"],
                                        serial_number = ss["serial_number"],
                                        model_name = ss["model_name"]) == True

                assert self.get_subsystems_list() == True

                for subsystem in self.ss_temp_list:
                    assert self.cli.add_listner_subsystem(
                            subsystem, self.helper.ip_addr[0], "1158" )[0] == True

            ####### array_config
            if static_dict["array"]["phase"] == "true":
                assert self.cli.reset_devel()[0] == True
                assert self.cli.list_device()[0] == True
                system_disks = self.cli.system_disks

                pos_array_list =  static_dict["array"]["pos_array"]
                for array in pos_array_list:
                    array_name = array["array_name"]
                    nr_data_drives = array["data_device"]
                    nr_spare_drives = array["spare_device"]

                    if len(system_disks) < (nr_data_drives + nr_spare_drives):
                        raise Exception("Array '{}' insufficient disk count {}. Required minimum {}".format(
                            array_name, len(system_disks), nr_data_drives + nr_spare_drives))

                    if array["auto_create"] == "false":
                        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
                        spare_disk_list = [system_disks.pop()]
                        assert self.cli.create_array(write_buffer=array["uram"],
                                                    data=data_disk_list,
                                                    spare=spare_disk_list,
                                                    raid_type=array["raid_type"],
                                                    array_name=array_name)[0] == True
                    else:
                        assert self.cli.autocreate_array(array["uram"], 
                                                        nr_data_drives,
                                                        array["raid_type"],
                                                        array_name = array_name,
                                                        num_spare = nr_spare_drives
                                                        )[0] == True

                        assert pos.cli.info_array(array_name=array_name)[0] == True
                        d_dev = set(pos.cli.array_info[array_name]["data_list"])
                        s_dev = set(pos.cli.array_info[array_name]["spare_list"])
                        system_disks = list(set(system_disks) - d_dev.union(s_dev))

                    if array["mount"] == "true":
                        write_back = True
                        if array["write_back"] == "false":
                            write_back = False
                        assert self.cli.mount_array(array_name=array_name,
                                             write_back=write_back)[0] == True

            ##### volume config
            if static_dict["volume"]["phase"] == "true":
                volumes = static_dict["volume"]["pos_volumes"]
                for vol in volumes:
                    array_name = vol["array_name"]
                    assert self.cli.list_volume(array_name)
                    old_vols = self.cli.vols
                    assert self.create_volume_multiple(array_name, vol["num_vol"],
                                                    vol_name=vol["vol_name_pre"],
                                                    size=vol["size"]) == True

                    assert self.cli.list_volume(array_name)
                    cur_vols = self.cli.vols
                    new_vols = list(set(cur_vols) - set(old_vols))

                    if vol["mount"]["phase"]:
                        subsystem_range = vol["mount"]["subsystem_range"]
                        nqn_pre = vol["mount"]["nqn_pre"]
                        start, end = map(int, subsystem_range.split("-"))
                        nqn_list = [f"{nqn_pre}{s}" for s in range(start, end + 1)]

                        """
                        nqn_list = []
                        for s in range(start, end + 1):
                            for subs in self.ss_temp_list:
                                if f"subsystem{s}" in subs:
                                    nqn_list.append(subs)
                        """
                        assert self.mount_volume_multiple(array_name, 
                                                    new_vols, nqn_list) == True
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
            logger.info(
                "Current maximum # of memory map areas per process is {}.".format(
                    current_max_map_count
                )
            )
            if current_max_map_count < max_map_count:
                logger.info(
                    "Setting maximum # of memory map areas per process to {}.".format(
                        max_map_count
                    )
                )
                cmd = "sudo sysctl -w vm.max_map_count={}".format(max_map_count)
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def run_shell_command(self, command: str, expected_exit_code: int = 0) -> bool:
        """method to run shell commands
        Args:
            command (str) : command to be executed
            expected_exit_code (int) : exit_code
        Returns:
            bool
        """
        try:
            out = self.ssh_obj.execute(
                command=command, expected_exit_code=expected_exit_code
            )

            self.shell_out = out
            return True
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def get_dir_list(self, dir_path: str = None) -> (bool, list):
        """
        method to get file content using cat command
        """
        try:
            if dir_path is None:
                return False
            cmd = "ls {}".format(dir_path)
            out = self.run_shell_command(cmd)
            content = None
            if out is True:
                content = self.shell_out
            return out, content
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False

    def get_file_content(self, file_path: str = None) -> bool:
        """
        method to get file content using cat command
        """
        try:
            if file_path is None:
                return False
            cmd = "cat {}".format(file_path)
            out = self.run_shell_command(cmd)
            content = None
            if out is True:
                content = self.shell_out
            return out, content
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
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
                logger.info(
                    "The udev rule is applied(udev_rule = {})".format(self.udev_rule)
                )
            else:
                self.udev_rule = False
                logger.info(
                    "The udev rule is not applied(udev_rule = {})".format(
                        self.udev_rule
                    )
                )
        return True

    def get_pos(self) -> bool:
        """
        method to dump all the get commmands o/p from POS CLI
        Returns:
            bool
        """
        logger.info("=============================SYSTEM==========================")
        assert self.cli.info_system()[0] == True
        logger.info("=============================ARRAY==========================")

        assert self.cli.list_array()[0] == True

        array_list = list(self.cli.array_dict.keys())
        if len(array_list) != 0:
            for array in array_list:
                assert self.cli.info_array(array_name=array)[0] == True

        logger.info("=============================VOLUME==========================")
        if len(array_list) != 0:
            for array in array_list:
                assert self.cli.list_volume(array_name=array)[0] == True

        logger.info("=============================DEVICE==========================")
        assert self.cli.list_device()[0] == True
        logger.info("=============================QOS============================")
        if len(array_list) != 0:
            for array in array_list:
                assert self.cli.list_volume(array_name=array)[0] == True
                if len(self.cli.vols) != 0:
                    for vol in self.cli.vols:
                        assert (
                            self.cli.list_volume_policy_qos(
                                volumename=vol, arrayname=array
                            )[0]
                            == True
                        )

        logger.info("=============================LOGGER==========================")
        assert self.cli.info_logger()[0] == True

        logger.info("=============================SUBSYSTEM==========================")
        assert self.cli.list_subsystem()[0] == True
        return True

    def Npor(self) -> bool:
        """method to perform NPOR
        Returns:
            bool
        """
        try:
            assert self.get_subsystems_list() == True
            assert self.cli.list_array()[0] == True
            array_list = list(self.cli.array_dict.keys())
            if len(array_list) == 0:
                logger.info("No Array Present in the config")
                return False
            else:
                for array in array_list:
                    if self.cli.array_dict[array].lower() == "mounted":
                        assert self.cli.list_volume(array_name=array)[0] == True
                        if len(self.cli.vols) == 0:
                            logger.info("No volumes found")
                        else:
                            for vol in self.cli.vols:
                                if (
                                    self.cli.vol_dict[vol]["status"].lower()
                                    == "mounted"
                                ):
                                    assert (
                                        self.cli.unmount_volume(
                                            volumename=vol, array_name=array
                                        )[0]
                                        == True
                                    )

            assert self.cli.stop_system()[0] == True
            assert self.cli.start_system()[0] == True
            uram_list = [f"uram{str(i)}" for i in len(array_list)]
            for uram in uram_list:
                assert self.cli.create_device(uram_name=uram)[0] == True
            assert self.cli.scan_device()[0] == True
            self.helper.get_mellanox_interface_ip()
            for ss in self.ss_temp_list:
                assert self.cli.create_subsystem(ss)[0] == True
                assert (
                    self.cli.add_listner_subsystem(
                        nqn_name=ss,
                        mellanox_interface=self.helper.ip_addr[0],
                        port="1158",
                    )[0]
                    == True
                )
            assert self.cli.list_array()[0] == True
            array_list = list(self.cli.array_dict.keys())
            if len(array_list) == 0:
                logger.info("No Array Present in the config")
                return False
            else:
                for array in array_list:
                    assert self.cli.mount_array(array_name=array)[0] == True
                    assert self.cli.list_volume(array_name=array)[0] == True
                    if len(self.cli.vols) == 0:
                        logger.info("No volumes found")
                    else:
                        ss_list = [ss for ss in self.ss_temp_list if array in ss]
                        assert (
                            self.mount_volume_multiple(self.cli.vols, nqn_list=ss_list)
                            == True
                        )

            return True
        except Exception as e:
            logger.error(f"SPOR failed due to {e}")
            return False
    
    def deleteAllVolumes(self, arrayname):
        """method to delete all volumes if any in a given array"""
        try:
            assert self.cli.list_array()[0] == True
            if arrayname  in list(self.cli.array_dict.keys()):
                assert self.cli.list_volume()[0] == True
                if len(self.cli.vols) == 0:
                        logger.info("No volumes found")
                        return True
                for vol in self.cli.vols:
                    assert self.cli.info_volume(array_name=arrayname, vol_name=vol)[0] == True
                    if self.cli.volume_info[arrayname][vol]["status"].lower() == "mounted":
                        assert self.cli.unmount_volume(volumename=vol, array_name=arrayname)[0] == True
                    assert self.cli.delete_volume(volumename=vol, array_name=arrayname)[0] == True
                return True
                                    
        except Exception as e:
            logger.error(e)
            return False