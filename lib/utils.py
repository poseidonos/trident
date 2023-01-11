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

import logger
import time
import re
import datetime
import random
import json
import traceback
import helper
import threadable_node 

logger = logger.get_logger(__name__)


class Client:
    """
    The Client objects contains methods for host application

    Args:
        ssh_obj : client paramiko object
        client_cleanup : " flag to clean up client" (Default: True)
    """

    def __init__(self, ssh_obj, client_cleanup: bool = True):
        
        self.ssh_obj = ssh_obj
        self.client_clean = client_cleanup
        self.helper = helper.Helper(ssh_obj)
        self.nqn_list = []
        self.mount_point = {}
        logger.info(f"creating client object on {ssh_obj.hostname}")
        if self.client_clean == True:
            self.client_cleanup()

    def close(self):
        """
        Method to close the ssh object
        """
        self.ssh_obj.close()

    def _add_nqn_name(self, nqn: str):
        """ Internal Method to add nqn name """
        if nqn in self.nqn_list:
            raise Exception(f"NQN {nqn} is already added")
            
        self.nqn_list.append(nqn)

    def _del_nqn_name(self, nqn: str):
        """ Internal Method to delete nqn name """
        if nqn not in self.nqn_list:
            raise Exception(f"NQN {nqn} is not added")

        self.nqn_list.remove(nqn)

    def _add_mount_point(self, device_name: str, mount_point: str):
        """ Internal Method to add mount point """
        if self.mount_point.exist(device_name):
            raise Exception("Device {} is already mounted to {}..".format(
                            device_name, mount_point))
        self.mount_point[device_name] = mount_point

    def _del_mount_point(self, mount_point: str, device_name: str = None):
        """ Internal Method to remove mount point """
        if not device_name:
            for dev, mp in self.mount_point.items():
                if mp == mount_point:
                    device_name = dev
                    break
        if not device_name:
            raise Exception("Invalid mount point {mount_point}")

        self.mount_point.pop(device_name)

    def reset(self, pos_run_status):
        """ Method to reset client """
        mount_points = list(self.mount_point.values())
        self.unmount_FS(fs_mount_pt=mount_points)
        self.nvme_disconnect(nqn=self.nqn_list) 
        pass

    def client_cleanup(self):
        """
        method to do client clean up
        """
        self.nvme_disconnect()
        self.load_drivers()
        self.dmesg_clear()

    def dmesg_clear(self):
        """
        method to clear Dmesg
        """

        self.ssh_obj.execute("dmesg -C")

    def reboot_node(self) -> bool:
        """
        Method to reboot the node
        Returns : bool
        """
        try:
            stdoutlines = []
            shell = self.ssh_obj.ssh.invoke_shell()
            node._shell_receive(shell, stdoutlines)

            if self.ssh_obj.username == "root":
                shell.send("shutdown -r now  " + "\n")
            else:
                shell.send("sudo shutdown -r now  " + "\n")
                shell.send(self.ssh_obj.password + "\n")
                node._shell_receive(shell, stdoutlines)
                shell.send(self.ssh_obj.password + "\n")

            logger.info("waiting 10 seconds for reboot")
            time.sleep(10)
            logger.info("Reboot node sucessfull")
            return True
        except Exception as e:
            logger.error("Error rebooting node because of Error {}".format(e))
            return False

    def reboot_with_reconnect(self, timeout: int = 600) -> bool:
        """
        Methods: To reboot the node and wait for it come up

        Args:
            timeout (int) : time to wait for not to come up (default 5 minutes)
        Returns:
         new_ssh obj, bool
        """
        self.reboot_node()
        count = 0
        new_ssh = None
        node_stats = None

        while True:
            try:
                new_ssh = SSHclient(
                    self.ssh_obj.hostname, self.ssh_obj.username, self.ssh_obj.password
                )
            except Exception as e:
                logger.info("node is still down {}".format(e))
                time.sleep(60)
                logger.info("waiting 60 seconds node to come  up ")
            count = count + 60
            if new_ssh:
                node_status = new_ssh.get_node_status()
            if count > timeout or node_stats == True:
                break

        if new_ssh:
            return new_ssh, True
        else:
            logger.error(traceback.format_exc())
            raise ConnectionError("Node failed to come up")

    def reconnect(self, timeout: int = 600) -> bool:
        """
        Methods: To reboot the node and wait for it come up

        Args:
            timeout (int) : time to wait for not to come up (default 5 minutes)
        Returns:
         new_ssh obj
        """
        count = 0
        new_ssh_obj = None
        node_status = None

        while True:
            try:
                new_ssh_obj = SSHclient(
                    self.ssh_obj.hostname, self.ssh_obj.username, self.ssh_obj.password
                )
            except Exception as e:
                logger.info("node is still down {}".format(e))
            logger.info("waiting 60 seconds node to come  up ")
            time.sleep(60)
            count = count + 60
            if new_ssh_obj:
                node_status = new_ssh_obj.get_node_status()
            if count > timeout or node_status == True:
                break

        if new_ssh_obj:
            return new_ssh_obj
        else:
            raise ConnectionError("Node failed to come up")

    def nvme(self, nvme_cmd: str) -> (bool, list):
        """
        Methods: Execution of nvme command

        Args:
            nvme_cmd (str) : nvme command to be executed
        Returns:
          bool, list

        """

        nvme_cmd_output = self.ssh_obj.execute(nvme_cmd)
        return nvme_cmd_output

    def nvme_format(self, device_name: str) -> (bool, list):
        """
        Method
        To format device using nvme cli

        Args:
            device_name (str) : Name of the device to be formated
        Returns:
            bool
        """
        try:
            logger.info("Formatting the device {} ".format(device_name))
            cmd = "nvme format {}".format(device_name)
            out = self.nvme(cmd)
            if "Success formatting namespace" in out[0]:
                logger.info("Successfully formatted the device ")
            else:
                raise Exception("formatting nvme device failed")
        except Exception as e:
            logger.error("nvme format command failed with exception {}".format(e))

            return False
        return True

    def nvme_id_ctrl(self, device_name: str, search_string: str = None) -> (bool, list):
        """
        Method to execute nvme id-ctrl nvme cli

        Args:
            device_name (str) name of the device
            search_string (str) Search Expression (default = None)
        Returns:
            bool, list
        """
        try:
            logger.info("Executing id-ctrl on  the device {} ".format(device_name))
            if search_string:
                cmd = "nvme id-ctrl {} | grep -w {}".format(device_name, search_string)
            else:
                cmd = "nvme id-ctrl {} ".format(device_name)
            out = self.ssh_obj.execute(cmd)
            if len(out) != 0:
                logger.info(
                    "Successfully executed nvme id-ctrl on the device {}".format(
                        device_name
                    )
                )
                return True, out
            else:
                raise Exception(
                    "Failed to execute nvme id-ctrl on the device {}".format(
                        device_name
                    )
                )
        except Exception as e:
            logger.error("nvme id-ctrl command failed with exception {}".format(e))

            return False, out

    def nvme_ns_rescan(self, cntlr_name: str) -> bool:
        """
        Method to execute nvme ns-rescan nvme cli

        Args:
            cntlr_name (str) Search for the name of the controller
        Returns:
            bool
        """
        try:
            logger.info("Executing ns-rescan on  the controller {} ".format(cntlr_name))
            cmd = "nvme ns-rescan {}".format(cntlr_name)
            out = self.ssh_obj.execute(cmd)
            if "No such file or directory" in out:
                raise Exception(
                    " Failed to rescan the controller {}".format(cntlr_name)
                )
            else:
                logger.info(
                    "Successfully rescaned the controller {}".format(cntlr_name)
                )
                return True
        except Exception as e:
            logger.error("nvme ns-rescan command failed with exception {}".format(e))

            return False

    def nvme_show_regs(
        self, device_name: str, search_string: str = None
    ) -> (bool, list):
        """
        Method to execute nvme show-regs nvme cli

        Args:
            device_name (str): name of the Device
            search_strings (str): Pattern to be matched (default = None)

        Returns:
            bool, list
        """
        try:
            logger.info("Executing show-regs on  the device {} ".format(device_name))
            if search_string:
                cmd = "nvme show-regs -H {} | grep -w {}".format(
                    device_name, search_string
                )
            else:
                cmd = "nvme show-regs -H {} ".format(device_name)
            out = self.ssh_obj.execute(cmd)
            logger.info("output of the command {} is {} ".format(cmd, out))
            if len(out) != 0:
                logger.info(
                    "Successfully executed nvme show-regs on the device {}".format(
                        device_name
                    )
                )
                return True, out
            else:
                raise Exception(
                    "Failed to execute nvme show-regs on the device {}".format(
                        device_name
                    )
                )
        except Exception as e:
            logger.error("nvme show-regs command failed with exception {}".format(e))

            return False, out

    def nvme_list_subsys(self, device_name: str) -> (bool, list):
        """
        Method to execute nvme list-subsys nvme cli

        Args:
            device_name (str) : device name

        Returns:
            bool, list
        """
        try:
            logger.info("Executing list-subsys on the device {} ".format(device_name))
            cmd = "nvme list-subsys {} -o json ".format(device_name)
            out = self.ssh_obj.execute(cmd)
            out1 = "".join(out)
            json_out = json.loads(out1)
            logger.info("output of the nvme list-subsys is {} ".format(json_out))
            if "Error" in out:
                raise Exception(
                    "Failed to execute nvme list-subsys on device {}".format(
                        device_name
                    )
                )
            else:
                logger.info(
                    "Successfully executed nvme list-subsys on device {}".format(
                        device_name
                    )
                )
                return True, json_out
        except Exception as e:
            logger.error("nvme list-subsys command failed with exception {}".format(e))

            return False, None

    def nvme_smart_log(
        self, device_name: str, search_string: str = None
    ) -> (bool, list):
        """
        Method to execute nvme smart-log nvme cli
        Args:
            device_name (str): name of the Device
            search_strings (str): Pattern to be matched (default = None)

        Returns:
            bool, list
        """
        try:
            logger.info("Executing smart-log  on  the device {} ".format(device_name))
            if search_string:
                cmd = "nvme smart-log {} | grep {} | awk  '{{print $3}}'".format(
                    device_name, search_string
                )
                logger.info(cmd)
            else:
                cmd = "nvme smart-log {} ".format(device_name)
            out = self.ssh_obj.execute(cmd)
            if len(out) != 0:
                logger.info(
                    "Successfully executed nvme smart-log on the device {}".format(
                        device_name
                    )
                )
                return True, out
            else:
                raise Exception(
                    "Failed to execute nvme smart-log on the device {}".format(
                        device_name
                    )
                )
        except Exception as e:
            logger.error("nvme smart-log command failed with exception {}".format(e))

            return False, None

    def os_version(self) -> str:
        """
        method To find OS version
        Returns:
            str
        """
        flag = [
            version
            for version in self.ssh_obj.execute("cat /etc/os-release")
            if "ubuntu" in version
        ]
        if len(flag):
            logger.info(
                "OS version is %s"
                % (flag[0].split("=")[1].strip("\n") + flag[1].split("=")[1].strip())
            )
            return flag[0].split("=")[1].strip("\n") + flag[1].split("=")[1].strip()

    def fio_generic_runner(
        self,
        devices: list,
        fio_user_data=None,
        IO_mode=True,
        expected_exit_code=None,
        run_async=False,
        json_out: str = None,
    ):
        """
        :method To run user provided fio cmd line from user
        :params fio_user_data :fio cmd line (default :none)
                devices: takes a list of either mount points or raw devices
                IO_mode : RAW IO(True)/File IO(False)
                expected_exit_code : used to handle the negative FIO scenario's, Need to pass the exit code of the executed FIO command 0 or 1
                json_out : name of the fio json
                run_async : used to run FIO in back ground
        :return : Boolean

        """
        try:
            if json_out:
                self.fio_out_json = (
                    f'{json_out}_{datetime.datetime.now().strftime("%Y-%m_%H_%M")}.json'
                )
            else:
                self.fio_out_json = (
                    f'fiojsonop_{datetime.datetime.now().strftime("%Y-%m_%H_%M")}.json'
                )
            if not IO_mode:  # File IO
                devices = list(map(lambda x: f"{x}/file.bin", devices))

            filename = ":".join(devices)

            if fio_user_data:
                fio_cmd = fio_user_data
            else:
                fio_cmd = "fio --name=S_W --runtime=5 --ioengine=libaio --iodepth=16 --rw=write --size=1g --bs=1m --direct=1"

            fio_cmd += " --filename={} --output-format=json --output={}".format(
                filename, self.fio_out_json
            )

            if run_async == True:
                async_out = self.ssh_obj.run_async(fio_cmd)
                return True, async_out
            else:
                outfio = self.ssh_obj.execute(
                    fio_cmd, get_pty=True, expected_exit_code=expected_exit_code
                )
                self.fio_parser()
                return True, outfio

        except Exception as e:
            logger.error("Fio failed due to {}".format(e))
            traceback.print_exc()
            return (False, None)

    def fio_parser(self) -> dict():
        """
        method to make specific information from fio output
        bw: KiB/s
        iops: iops
        clat: nsec
        """
        logger.info("am here")
        cmd = f"cat {self.fio_out_json}"
        str_out = self.ssh_obj.execute(cmd)
        printout = "".join(str_out)
        logger.info(printout)
        self.fio_par_out = {}
        str_out = "".join(str_out).replace("\n", "")
        jout = json.loads(str_out)

        self.fio_par_out["read"] = {
            "bw": jout["jobs"][0]["read"]["bw"],
            "iops": jout["jobs"][0]["read"]["iops"],
            "clat": jout["jobs"][0]["read"]["clat_ns"],
        }
        self.fio_par_out["write"] = {
            "bw": jout["jobs"][0]["write"]["bw"],
            "iops": jout["jobs"][0]["write"]["iops"],
            "clat": jout["jobs"][0]["write"]["clat_ns"],
        }
        return True

    def fio_verify_qos(self, qos_data: dict, fio_out: dict, num_dev: int) -> bool:
        """
        Method to verify the fio output in adhare the qos throttling
        qos_data: QOS data dictionary
                    {max_iops, max_bw}
        fio_out: FIO output dictionary
                    {bw, iops, clat}
        num_dev: Number of nvme device listed
        """
        logger.info(f"Compare fio output '{fio_out}' and qos values '{qos_data}'")

        bs, kiops = 4096, 1000
        qos_max_bw = qos_data["max_bw"]
        qos_max_iops = qos_data["max_iops"]
        fio_bw = fio_out["bw"]
        fio_iops = fio_out["iops"]

        avg_fio_bw = float(fio_bw) / num_dev
        avg_fio_iops = float(fio_iops) / num_dev
        result = False

        if qos_max_bw < (qos_max_iops * bs * kiops / (1024 * 1024)):
            logger.info(
                "avg fio bw: {} ({}/{} - total bw/num of device). qos max bw {}".format(
                    avg_fio_bw, fio_bw, num_dev, qos_max_bw
                )
            )
            if avg_fio_bw < qos_max_bw and avg_fio_bw > qos_max_bw * 0.95:
                result = True
        else:
            qos_max_iops = qos_max_iops * kiops
            logger.info(
                "avg fio iops: {} ({}/{} - total iops/num of device). qos max iops {}".format(
                    avg_fio_iops, fio_iops, num_dev, qos_max_iops
                )
            )
            if avg_fio_iops < qos_max_iops and avg_fio_iops > qos_max_iops * 0.95:
                result = True

        return result

    def is_file_present(self, file_path: str) -> bool:
        """
        Method to verify if file present of not

        Args:
            file_path (str): file path
        Returns:
                bool
        """
        try:
            out = self.ssh_obj.execute(
                "if test -f {}; then     echo ' exist'; fi".format(file_path)
            )
            if out:
                if "exist" in out[0]:
                    logger.info("File  {} exist".format(file_path))
                    return True
            else:
                raise Exception("file {}  does not exist".format(file_path))
        except Exception as e:
            logger.error("command failed with exception {}".format(e))

            return False

    def create_File_system(self, device_list: list, fs_format: str = "ext3") -> bool:
        """
        Creates MKFS FS on different devices

        Args:
            device_list (list) : list of devices
            fs_format (str) : format of the FS (default ext3)
        Returns:
            bool
        """
        try:
            if len(device_list) == 0:
                raise Exception("No devices Passed")
            else:
                for device in device_list:
                    if fs_format == "xfs":
                        format_cmd = "yes |sudo mkfs.{} -f  {}".format(
                            fs_format, device
                        )
                    else:
                        format_cmd = "yes |sudo mkfs.{} {}".format(fs_format, device)
                    self.ssh_obj.execute(format_cmd, get_pty=True)
                return True
        except Exception as e:
            logger.error("command failed with exception {}".format(e))

            return False

    def mount_FS(
        self, device_list: list, fs_mount_dir: str = "/tmp", options: str = None
    ) -> (bool, list):
        """
        method to Mount Fs to device

        Args:
             device_list (list) :devices to mount
             fs_mount_dir (str) :if None will create dir in /tmp
             option if not None will add to mount cmd
                eg --force
        Returns:
            bool, list of dir
        """
        try:
            logger.info("device_list={}".format(device_list))
            for device in device_list:
                device_str = device.split("/dev/")[1]
                fs_mount = f"{fs_mount_dir}/media_{device_str}"
                logger.info(f"Mount Point : {fs_mount}")
                if self.is_dir_present(fs_mount) == True:
                    logger.error(f"{fs_mount} already exists.. creating a new dir inside")
                    fs_mount = "{}/{}".format(fs_mount, random.randint(0, 1000))
                    if self.is_dir_present(fs_mount) == True:
                        raise Exception("{fs_mount} already exists, Please unmount and try again!")

                fs_make = f"mkdir -p {fs_mount}"
                f_mount = f"mount {device} {fs_mount}"
                if options:
                    f_mount = f"{f_mount} {options}"

                try:
                    self.ssh_obj.execute(fs_make, get_pty=True)
                    self.ssh_obj.execute(f_mount, get_pty=True)
                    mnt_verify_cmd = "mount | grep {} ".format(fs_mount)
                    verify = self.ssh_obj.execute(mnt_verify_cmd)
                    if len(verify) == 0:
                        raise Exception("Mount Failed! PLease try again")
                    else:
                        for mount_pts_devices in verify:
                            if fs_mount in mount_pts_devices:
                                self._add_mount_point(device, fs_mount)
                except Exception as e:
                    logger.error("Mounting {} to {} failed due to {}".format(
                                 fs_mount, device, e))
                    return (False, None)
            return (True, list(self.mount_point.values()))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return (False, None)

    def unmount_FS(self, fs_mount_pt: list) -> bool:
        """
        method to unmount file system

        Args:

            fs_mount_pt (str): Name of the directory to unmount
        Returns:
            bool
        """
        try:
            for mnt in fs_mount_pt:
                umount_cmd = "umount {}".format(mnt)
                out = self.ssh_obj.execute(umount_cmd)
                if out:
                    raise Exception(f"Failed to unmount '{mnt}'. Cli Error: '{out}'")
                else:
                    logger.info(f"Successfully unmounted '{mnt}'")

                logger.info("Deleting filesystem after unmounting")
                assert self.delete_FS(fs_mount_pt=mnt) == True
                
                self._del_mount_point(mnt)
            return True
        except Exception as e:
            logger.error("Unmount FS failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def delete_FS(self, fs_mount_pt: bool) -> bool:
        """
        Method to delete a directory, used to delete directory after unmount
        Args:
            fs_mount_pt (str) : dir of mount pt
        Returns:
            bool

        """
        try:
            rm_cmd = "rm -fr {}".format(fs_mount_pt)
            out = self.ssh_obj.execute(rm_cmd)
            if out:
                raise Exception(f"Failed to delete '{fs_mount_pt}'. Cli Error: '{out}'")

            if self.is_dir_present(fs_mount_pt) is True:
                raise Exception("File found after deletion")
            else:
                return True
        except Exception as e:
            logger.error("Delete FS failed with exception {}".format(e))

            return False

    def is_dir_present(self, dir_path: str) -> bool:
        """
        Method to verif if directory is present or not
        Args:
            dir_path (str) : path of the dir
        Returns:
            Bool

        """
        try:
            out = self.ssh_obj.execute(
                "if test -d {}; then     echo ' exist'; fi".format(dir_path)
            )
            if out:
                if "exist" in out:
                    logger.info("directory  {} exist".format(dir_path))
                    return True
            else:
                logger.warning("directory {}  does not exist".format(dir_path))
                return False
        except Exception as e:
            logger.error("error finding directory {}".format(e))
            return False

    def nvme_connect(self, nqn_name: str, mellanox_switch_ip: str,
                     port: str, transport: str = "TCP") -> bool:
        """
        Starts Nvme connect at the host

        Args:
        nqn_name (str) :Name of SS
        mellanox_switch_ip (str): mellanox switch interface ip
        port (str): port
        transport (str) : transport connection protocol (default : TCP)
        """
        try:
            if self.client_clean == False:
                self.load_drivers()
            cmd = "nvme connect -t {} -s {} -a {} -n {}".format(
                transport.lower(), port, mellanox_switch_ip, nqn_name
            )
            logger.info("Running command {}".format(cmd))
            out = self.ssh_obj.execute(cmd)

            self._add_nqn_name(nqn_name)
            return True
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))

            return False

    def ctrlr_list(self) -> (bool, list):
        """
        method to find the list of controllers connected

        Returns:
        bool,count
        """
        cmd = "ls /dev/nvme*"
        out = self.ssh_obj.execute(cmd)
        if len(out) < 2:
            logger.error("No controllers found")
            return (False, None)
        else:
            if "/dev/nvme-fabrics\n" in out:
                out.remove("/dev/nvme-fabrics\n")
        temp, final = [], []
        for device in out:
            ctrlr = re.findall("/dev/nvme[0-9]+", device)
            temp.append(ctrlr[0])

        for i in temp:
            if i not in final:
                final.append(i)

        return (True, final)

    def load_drivers(self) -> bool:
        """method to load drivers"""

        driver_list = ["tcp", "nvme"]
        for drive in driver_list:
            cmd = f"modprobe {drive}"
            self.ssh_obj.execute(cmd)
        return True

    def nvme_disconnect(self, nqn: list = [], timeout: int = 60) -> bool:
        """
        Method to disconnect nvmf ss
        Args:
            nqn (list) : list of ss to be disconnected if empty -d  will be used
            timeout : waiting time for disconnect to pass (default 60 sec)
        Returns:
            bool

        """
        try:
            logger.info("Disconnecting nvme devices from client")
            count = 0
            while True:
                out = self.ctrlr_list()
                cmd_list = []
                if out[1] is not None:
                    if len(nqn) != 0:
                        logger.info("Disconnecting Subsystem")
                        for nqn_name in nqn:
                            cmd_list.append(f"nvme disconnect -n {nqn_name}")
                            
                    else:
                        for ctrlr in out[1]:
                            cmd_list.append("nvme disconnect -d {}".format(ctrlr))
                           
                threadable_node.sync_parallel_run(self.ssh_obj, cmd_list=cmd_list)
                self.nvme_list()
                if len(self.nvme_list_out) == 0:
                    logger.info("Nvme disconnect passed")
                    return True
                else:
                    logger.info("retrying disconnect in 5 seconds")
                    count += 5
                    time.sleep(5)
                    if count > timeout:
                        break
            if len(self.nvme_list_out) != 0:
                raise Exception("nvme disconnect failed")

            self._del_nqn_name(nqn_name)
        except Exception as e:
            logger.error("command failed wth exception {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def nvme_list(self, model_name: str = "POS_VOLUME") -> bool:
        """
        Method to get the nvme list
        Args:
            model_name (str) mode name in nvme list (default : POS_VOLUME)
        Returns:
            Bool
        """
        try:
            cmd = "nvme list"
            time.sleep(5)
            out = self.nvme(cmd)
            self.nvme_list_out = []
            for line in out:
                logger.info(line)
                if model_name in line:
                    list_out = line.split(" ")
                    self.nvme_list_out.append(str(list_out[0]))
            if len(self.nvme_list_out) == 0:
                logger.debug("no devices listed")
                return False
        except Exception as e:
            logger.error("command execution failed with exception {} ".format(e))

            return False
        return True

    def nvme_discover(
        self, nqn_name: str, mellanox_switch_ip: str, port: str, transport: str = "tcp"
    ) -> bool:
        """
        method to discover nvme subsystem
        Args :
              nqn_name (str): Subsystem name
              mellanox_switch_ip (str): mlnx_ip
              port (str) : port number
              transport (str) : transport protocol (default : TCP)
        Returns :
            bool
        """
        try:

            self.load_drivers()
            discover_cmd = (
                "nvme discover --transport={} --traddr={} -s {}  --hostnqn={}".format(
                    transport, mellanox_switch_ip, port, nqn_name
                )
            )
            logger.info("Running command {}".format(discover_cmd))
            out = self.ssh_obj.execute(discover_cmd)
            flag = 0
            for line in out:
                if nqn_name[0] in line or mellanox_switch_ip in line:
                    flag = 1
                    break
            if flag == 1:
                return True
            else:
                logger.error("Discover failed")
                return False
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def nvme_flush(self, dev_list: list) -> bool:
        """
        methood to execute nvme flush
        Args
            devices_list (list) list of nvme devices to be passed in list
        Returns bool
        """
        try:
            for dev in dev_list:
                cmd = "nvme flush {} -n 0x1".format(dev)
                out = self.ssh_obj.execute(cmd)
                logger.info(out)
                out1 = "".join(out)
                logger.info(out1)
                if "NVMe Flush: success" in out[0].strip():
                    logger.info(
                        "successfully executed nvme flush on device {}".format(dev)
                    )
                else:
                    raise Exception(
                        "nvme flush command failed on device {}".format(dev)
                    )
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))

            return False
        return True

    def check_system_memory(self):
        """method to check the system mem info in the host"""
        assert self.helper.check_system_memory() == True

    def part_num(self, Device_name: str = None, part: bool = True) -> (bool, list, int):
        """method to find number of partitions presnt on a device"""

        try:
            if part is False:
                cmd = "lsblk | grep nvme||true"
            else:
                dev_name = Device_name.split("/dev/")[1]
                cmd = "lsblk | grep {}p||true".format(dev_name)

            out = self.ssh_obj.execute(cmd)
            if len(out) is 0:
                logger.info("No partitions found")
                return True, None, len(out)
            else:
                temp = []
                if part is True:
                    logger.info(
                        "number of partitions in {} : {}".format(Device_name, len(out))
                    )
                    reg = r"{}p\d+".format(dev_name)
                else:
                    reg = r"nvme\d+n\d+"

                for i in out:
                    regx = re.search(reg, i)
                    temp.append(regx.group())

                return True, temp, len(out)

        except Exception as e:
            logger.error("failed to get partition data due to {}".format(e))
            return False, None, None

    def create_part(self, device_name: str, part_size: str) -> (bool, list):
        """
        Method to create partition on a given block device
        """
        try:
            out = self.part_num(Device_name=device_name)
            num_part = out[2]
            if out[0] is True:
                cmd = "fdisk {}".format(device_name)
                out = self.ssh_obj.shell_execute(
                    cmd, ["n", "p", "\n", "+{}".format(part_size), "Y", "w"], wait=3
                )

                out = self.part_num(Device_name=device_name)
                if num_part >= out[2]:
                    logger.error("Creation of partion failed")
                    return False, None
                else:
                    temp = []
                    for i in out[1]:
                        dev = "/dev/{}".format(i)
                        temp.append(dev)
                    return True, temp
        except Exception as e:
            logger.error("creating partition failed due to {}".format(e))
            return False, None
