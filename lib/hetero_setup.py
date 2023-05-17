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

from enum import Enum
import json
import os
import re
import pickle
from os import path

import logger

logger = logger.get_logger(__name__)


def display_message(message):
    logger.info("*" * 50)
    logger.info(message)
    logger.info("*" * 50)


class NS_State(Enum):
    UNKNOWN = 0
    ACTIVE = 1
    INACTIVE = 2
    ALLOCATED = 3
    UNALLOCATED = 4



class NVMe_Command:
    def __init__(self, conn: object) -> None:
        """
        conn : Connection Object
        """
        self.conn = conn  # SSH Connection Object
        pass

    def nvme_submit(self, command: str, json_out: bool = True) -> bool:
        """
        command: nvme cli command
        """
        command = f"nvme {command}"
        if json_out:
            command += " -o json"

        out = self.conn.execute(command)
        # TODO fix execute api
        try:
            out = "".join(out)
        except:
            out = "".join(out[0])

        if "No such file or directory" in out:
            logger.error(f"{out}")
            return False

        self.response = "".join(out)
        return True

    def identify_controller(self, nvme_dev: str, json_out: bool = True) -> bool:
        """
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        """
        id_ctrl_cmd = f"id-ctrl {nvme_dev}"

        if self.nvme_submit(id_ctrl_cmd, json_out):
            self.id_ctrl = self.response
        else:
            logger.error(f"Identify controller command failed")
            return False

        return True

    def indentify_ns(self, nvme_dev: str, nsid: int = 1, json_out: bool = True) -> bool:
        """
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        """
        id_ns_cmd = f"id-ns {nvme_dev} -n {nsid}"

        if self.nvme_submit(id_ns_cmd, json_out):
            self.id_ns = self.response
        else:
            logger.error(f"Identify namespace command failed")
            return False

        return True

    def list_ns(self, nvme_dev: str, nsid: int = None) -> bool:
        """
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        """
        list_ns_cmd = f"list-ns {nvme_dev}"

        if nsid != None:
            list_ns_cmd += f" -n {nsid}"

        if self.nvme_submit(list_ns_cmd, json_out=False):
            self.ns_list = self.response
        else:
            logger.error(f"List namespace command failed")
            return False

        return True

    def list_ctrl(self, nvme_dev: str, nsid: int = None) -> bool:
        """
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        """
        list_ctrl_cmd = f"list-ctrl {nvme_dev}"

        if nsid != None:
            list_ctrl_cmd += f" -n {nsid}"

        if self.nvme_submit(list_ctrl_cmd, json_out=False):
            self.ctrl_list = self.response
        else:
            logger.error(f"List controller command failed")
            return False

        return True

    def attach_detach_ns(
        self, attach: bool, nvme_dev: str, nsid: int, ctrl_id: int
    ) -> bool:
        """
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        ctrl_id: Controller ID
        """
        if attach:
            attach_detach = "attach"
        else:
            attach_detach = "detach"

        cmd = f"{attach_detach}-ns {nvme_dev} -n {nsid} -c {ctrl_id}"

        if self.nvme_submit(cmd, json_out=False):
            if f"{attach_detach}-ns: Success, nsid:{nsid}" in self.response:
                return True

        logger.error(f"{attach_detach.title()} Namespace command failed")
        return False

    def delete_ns(self, nvme_dev: str, nsid: int) -> bool:
        """
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        """
        delete_ns_cmd = f"delete-ns {nvme_dev} -n {nsid}"

        if self.nvme_submit(delete_ns_cmd, json_out=False):
            if f"delete-ns: Success, deleted nsid:{nsid}" in self.response:
                return True

        logger.error(f"Delete Namespace command failed")
        return False

    def create_ns(self, nvme_dev: str, size: int, flbas: int) -> bool:
        """
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID

        """
        create_ns_cmd = f"create-ns {nvme_dev} -s {size} -c {size} -f {flbas}"

        if self.nvme_submit(create_ns_cmd, json_out=False):
            match = r"create-ns: Success, created nsid:(\d+)"
            matched = re.search(match, self.response)
            if matched:
                self.new_nsid = int(matched.group(1))
                return True

        logger.error(f"Create Namespace command failed")
        return False

    def list_nvme(self) -> bool:
        list_nvme_cmd = "list"

        if self.nvme_submit(list_nvme_cmd, json_out=True):
            self.list_nvme = self.response
            return True

        logger.error(f"List NVMe command failed")
        return False


class NVMe_Dev(NVMe_Command):
    def __init__(
        self, ssh_obj: object, name: str, serial_number: str = None, bdf: str = None
    ) -> None:
        self.conn = ssh_obj
        self.name = self._set_device_name(name)
        self.device_path = f"/dev/{self.name}"  # /dev/nvme0
        self.serial_number = serial_number
        self.bdf = bdf
        self.is_mounted = False
        self.removed = False
        # Mark true when device is mapped with kernel space
        self.kernal_mapped = True
        self.nss = []  # List of Namespace Objects
        self.ctrl = None  # Controller Object
        self.nss_org = []  # Store Namespace Original Config
        self.ns_created = False  # Mark true when new NS are created
        self.ns_deleted = False  # Mark true when existing NS are deleted
        # Mark true when drive original status is restored
        self.ns_restored = False

    class Namespace:
        def __init__(
            self, nsid: int, size: int = 0, state: str = NS_State.UNKNOWN
        ) -> None:
            self.nsid = nsid  # Namespace ID
            self.size = size  # Namespace Size
            self.state = state  # Namespace State
            self.nlbaf = None  # Number of LBA format
            self.flbas = None  # Selected LBA Format
            self.lba_format = {}  # LBA Format Decode
            self.lba_format["metadata"] = 0  # Metadata Size in Bytes
            self.lba_format["data"] = 0  # Data Size in Bytes
            self.ctrl_list = []  # Attached Controller

        def __str__(self) -> str:
            return (
                f"\nNamespace Id    : {self.nsid} "
                f"\nNS Size         : {self.size} "
                f"\nNS State        : {self.state} "
                f"\nNr of Formats   : {self.nlbaf} "
                f"\nLBA Format      : {self.lba_format} "
                f"\nAttached Ctrl   : {self.ctrl_list} "
            )

    class Controller:
        def __init__(self, cntlid: int = 0) -> None:
            self.controller_id = cntlid  # Controller Id
            self.serial_number = None  # Controller Serial Number
            self.total_nvm_cap = 0  # Total NVM Capacity
            self.num_namespace = 0  # Max Number of Namespace
            self.ns_mgt_supported = False  # NS Management and Attachment Supported
            self.ns_fmt_supported = False  # Format NVM Supported

        def __str__(self) -> str:
            return (
                f"\nController Id      : {self.controller_id} "
                f"\nSerial Number      : {self.serial_number} "
                f"\nNVM Capacity       : {self.total_nvm_cap} "
                f"\nNumber Of NS       : {self.num_namespace} "
                f"\nNS Mgmt Supported  : {self.ns_mgt_supported} "
                f"\nFormat Supported   : {self.ns_fmt_supported} "
            )

    def _set_device_name(self, name):
        name = name.lower()
        match = re.search(r"(nvme\d+)", name)
        if match:
            return match.group(1)
        else:
            raise Exception("Device namve is not right format")

    def get_device_path(self):
        return self.device_path

    def get_serial_number(self):
        if not self.serial_number:
            logger.warning("Serial number is not set")
        return self.serial_number

    def verify_dev_mount(self) -> bool:
        cmd = f"cat /proc/mounts | grep {self.device_path}n"
        res = self.conn.execute(cmd)
        if res:
            self.is_mounted = False
            logger.info(f"Device {self.name} is not mounted")
        else:
            self.is_mounted = True
            logger.info(f"Device {self.name} is mounted. {res[0]}")

        return self.is_mounted

    def get_ctrl_object(self):
        if not self.ctrl:
            logger.warning("Controller object is not created.")

        return self.ctrl

    def get_nss_object_list(self):
        if not self.nss_org:
            logger.warning("Namespace object is not created.")

        return self.nss_org

    def load_info(self) -> bool:
        # Issue Identify Controller
        nvme_dev = self.get_device_path()
        if not self.identify_controller(nvme_dev):
            logger.error("Failed to get controller info")
            return False

        id_ctrl = json.loads(self.id_ctrl)
        ctrl = self.Controller(int(id_ctrl["cntlid"]))

        ctrl.serial_number = id_ctrl["sn"]
        ctrl.total_nvm_cap = id_ctrl["tnvmcap"]
        ctrl.num_namespace = int(id_ctrl["nn"])
        ctrl.ns_mgt_supported = int(id_ctrl["oacs"]) & 0x4 == 0x4
        ctrl.ns_fmt_supported = int(id_ctrl["oacs"]) & 0x1 == 0x1

        self.ctrl = ctrl
        self.serial_number = ctrl.serial_number
        logger.info(f"Controller Info: {ctrl}")

        if not self.list_ns(nvme_dev):
            logger.error("Failed to get active namespace list")
            return False

        nsid_list = re.findall(r"0x[\da-f]+", self.ns_list)
        nsid_list = list(map(lambda x: int(x, 0), nsid_list))
        logger.info(f"Namespace List: {nsid_list}")

        for index, nsid in enumerate(nsid_list):
            if not self.indentify_ns(nvme_dev, json_out=True):
                logger.error(f"Failed to get namespace{nsid} info")
                return False

            id_ns = json.loads(self.id_ns)

            ns = self.Namespace(nsid)
            ns.size = id_ns["nsze"]
            ns.state = NS_State.ACTIVE
            ns.nlbaf = int(id_ns["nlbaf"])
            ns.flbas = int(id_ns["flbas"]) & 0xF
            ns.lba_format["metadata"] = int(id_ns["lbafs"][ns.flbas]["ms"])
            ns.lba_format["data"] = 2 ** int(id_ns["lbafs"][ns.flbas]["ds"])

            if not self.list_ctrl(nvme_dev):
                logger.error(f"Failed to get controller list")
                return False

            ctrl_list = re.findall(r"0x[\da-f]+", self.ctrl_list)
            ns.ctrl_list = list(map(lambda x: int(x, 0), ctrl_list))

            logger.info(f"Namespace Info: {ns}")
            self.nss.append(ns)

        if not self.nss_org:
            self.nss_org = self.nss[:]

        self.verify_dev_mount()

        return True

    def print_info(self, all: bool = True) -> None:
        logger.info(f"{self.ctrl}")
        logger.info(f"{self.ns_list}")
        # Issue List Namespace
        # Issue Identify Namespace to all NS
        pass

    def restore(self) -> bool:
        """ """
        nvme_dev = self.get_device_path()
        if not self.ns_created and not self.ns_deleted:
            logger.info(f"Skipped! The drive {nvme_dev} is in original state")
            return True

        if self.nss:
            if not self.cleanup_ns():
                return False

        for ns_obj in self.nss_org:
            nsid = ns_obj.nsid
            logger.info(f"Restore namespace [nsid: {nsid}]")
            if not self.create_ns(
                nvme_dev=nvme_dev, size=ns_obj.size, flbas=ns_obj.flbas
            ):
                logger.error(f"Failed to create ns[{nsid}]")
                return False
            if nsid != self.new_nsid:
                logger.warning(f"Created NSID[{self.new_nsid}] match failed")

            for ctrl_id in ns_obj.ctrl_list:
                # Attach NS
                if not self.attach_detach_ns(
                    attach=True, nvme_dev=nvme_dev, nsid=self.new_nsid, ctrl_id=ctrl_id
                ):
                    logger.error(
                        f"Failed to attach ns[{self.new_nsid}] ctrl[{ctrl_id}]"
                    )
                    return False

        self.ns_restored = True
        self.ns_created = False
        self.ns_deleted = False
        return True

    def cleanup_ns(self) -> bool:
        nvme_dev = self.get_device_path()
        while self.nss:
            ns_obj = self.nss[0]
            nsid = ns_obj.nsid
            for ctrl_id in ns_obj.ctrl_list:
                # Detach NS
                logger.info(f"Detach namespace [nsid: {nsid}]")
                if not self.attach_detach_ns(
                    attach=False, nvme_dev=nvme_dev, nsid=nsid, ctrl_id=ctrl_id
                ):
                    logger.error(f"Failed to detach ns[{nsid}] ctrl[{ctrl_id}]")
                    return False

            # Delete NS
            logger.info(f"Delete namespace [nsid: {nsid}]")
            if not self.delete_ns(nvme_dev=nvme_dev, nsid=nsid):
                logger.error(f"Failed to delete ns[{nsid}]")
                return False

            self.nss.pop(0)

        self.ns_deleted = True
        return True

    def setup_ns(self, ns_config_list: list) -> bool:
        """
        ns_config: List of Dict of Namespace Config
                    [ { 'num_namespace': 1,
                        'ns_size': '19GiB',
                        'attach': True} ]

        """
        nvme_dev = self.get_device_path()
        if self.nss:
            logger.warning("Remove existing namespace")
            if not self.cleanup_ns():
                logger.error("Failed to remove existing namespaces")

        for ns_config in ns_config_list:
            ns_size = ns_config["ns_size"]

            matched = re.search(r"(\d+[.\d]+)(\w+)", ns_size)
            if matched:
                size = float(matched.group(1))
                unit = matched.group(2).lower()
                # Conver to Bytes
                if unit in ["gib", "gb"]:
                    size = size * 1024 * 1024 * 1024
                elif unit in ["tib", "tb"]:
                    size = size * 1024 * 1024 * 1024 * 1024
                else:
                    logger.error("Invalid Size")
                    return False
            else:
                logger.error("Invalid Size")
                return False

            # TODO add logic to handle multiple block size
            flbas = 0
            size = int(size // 512)

            for nr in range(ns_config["num_namespace"]):
                if not self.create_ns(nvme_dev=nvme_dev, size=size, flbas=flbas):

                    logger.error("Failed to create namespace")
                    return False
                nsid = self.new_nsid
                ctrl_id = self.ctrl.controller_id

                ns_obj = self.Namespace(nsid=nsid)
                ns_obj.size = size
                ns_obj.state = NS_State.ALLOCATED
                ns_obj.flbas = flbas
                ns_obj.lba_format["metadata"] = 0
                ns_obj.lba_format["data"] = 512

                if ns_config.get("attach", True):
                    if not self.attach_detach_ns(
                        attach=True, nvme_dev=nvme_dev, nsid=nsid, ctrl_id=ctrl_id
                    ):
                        logger.error("Failed to attach namespace")
                        return False
                    ns_obj.state = NS_State.ACTIVE

                self.nss.append(ns_obj)

        self.ns_created = True
        return True

    def is_dev_exists(self) -> bool:
        pass

    def bind_kernel_space(self) -> bool:
        pass

    def unbind_kernel_space(self) -> bool:
        pass

    def bind_user_space(self) -> bool:
        pass

    def bind_user_space(self) -> bool:
        pass


class TargetHeteroSetup:
    def __init__(
        self, ssh_obj: object,  hetero_setup_data: dict = None, pos_as_service = "true"
    ) -> None:
        self.ssh_obj = ssh_obj
        
        self.hetero_setup_data = hetero_setup_data
        self.nvme_test_device = {}
        self.nvme_sys_devices = {}
        self.nvme_devices = []
        self.nvme_device_scanned = False
        self.pos_as_service = pos_as_service

    def execute(self, command):
        try:
            response = self.ssh_obj.execute(command)
            print(type(response))
            print(response)
            if type(response) == "tuple":
                return None
            else:
                return " ".join(response)
        except Exception as e:
            logger.error(f"Exception occured {e}")

    def _get_nvme_device_list(self):
        cmd = 'ls /dev/nvme* | grep -E "nvme[0-9]{1,3}$"'
        nvme_device = self.execute(cmd)
        device_list = re.findall(r"nvme\d+", nvme_device)
        return device_list

    def scan_nvme_devices(self, device_list=None, force=True):
        device_list = device_list or self._get_nvme_device_list()

        if self.nvme_device_scanned and force == False:
            logger.info("NVMe device scan olready done. Use force to rescan")
            return True

        display_message("Started: NVMe device scan")
        for dev in device_list:
            nvme_dev = NVMe_Dev(ssh_obj=self.ssh_obj, name=dev)
            self.nvme_sys_devices[dev] = nvme_dev
            if not nvme_dev.load_info():
                return False

        self.nvme_device_scanned = True
        display_message("Completed: NVMe device scan")

        return True

    def get_device_sn_dict(self):
        device_dict = {}

        for dev in self.nvme_sys_devices.values():
            sn = dev.get_serial_number()
            device_dict[sn] = dev

        return device_dict

    def get_test_device_dict(self):
        if not self.nvme_test_device:
            logger.warning("Test device list is empty")

        return self.nvme_test_device

    def _do_spdk_setup_reset(self) -> bool:
        reset_cmd = "/usr/local/lib/spdk/scripts/setup.sh reset"

        out = self.ssh_obj.execute(reset_cmd)
        try:
            out = "".join(out)
        except:
            out = "".join(out[0])

        return True

    def save_test_device_state(self, file_name: str):
        if path.exists(file_name):
            logger.error(f"Pickle file {file_name} already exist.")
            logger.error(f"Recover the data OR Delete the file")
            return False

        nvme_dev_data = {}
        for dev_name, dev_obj in self.nvme_test_device.items():
            conn_bkp = dev_obj.conn
            dev_obj.conn = None
            nvme_dev_data[dev_name] = dev_obj

        try:
            with open(file_name, "wb") as fp:
                pickle.dump(nvme_dev_data, fp)

            logger.info(f"Pickle dump is created: {file_name}")
        except Exception as e:
            logger.error(f"Failed to load object. {e}")
            return False

        for dev_obj in self.nvme_test_device.values():
            dev_obj.conn = conn_bkp

        return True

    def load_test_device_state(self, file_name):
        try:
            if not path.exists(file_name):
                logger.error(f"File {file_name} dose not exist")
                return False

            with open(file_name, "rb") as fp:
                data = pickle.load(fp)
                self.recovered_nvme_dev_data = data
        except Exception as e:
            logger.error(f"Failed to load object {e}")
            return False

        return True

    def load_test_devices(self, device_list: list, recovery_file: str) -> bool:
        """
        device_list: i.e ['nvme0', 'nvme1']
        """
        if not self.scan_nvme_devices():
            logger.error("NVMe device scan Failed")
            return False

        sys_nvme_devs = self.nvme_sys_devices.keys()
        logger.info(f"System NVMe Devices : {list(sys_nvme_devs)}")

        for dev_name in device_list:
            if dev_name in sys_nvme_devs:
                nvme_dev = self.nvme_sys_devices[dev_name]
                if not nvme_dev.is_mounted:
                    self.nvme_test_device[dev_name] = nvme_dev
                else:
                    logger.info(f"Test device {dev_name} mounted")
                    return False
            else:
                logger.error(f"Test device {dev_name} does not exist")
                return False

        if not self.save_test_device_state(recovery_file):
            logger.error("Failed to save test device info")
            return False

        return True

    def recover_test_devices(self, recovery_file) -> bool:
        """ """
        if not self.load_test_device_state(recovery_file):
            logger.error("Failed to read test device info")
            return False

        if not self.scan_nvme_devices():
            logger.error("NVMe device scan Failed")
            return False

        sys_nvme_devs = self.nvme_sys_devices.keys()
        logger.info(f"System NVMe Devices : {list(sys_nvme_devs)}")

        for dev_name, dev_data in self.recovered_nvme_dev_data.items():
            dev_sn = dev_data.get_serial_number()
            sys_dev_ns_dict = self.get_device_sn_dict()
            if dev_sn in sys_dev_ns_dict.keys():
                nvme_dev = self.nvme_sys_devices[dev_name]
                if not nvme_dev.is_mounted:
                    self.nvme_test_device[dev_name] = nvme_dev
                    nvme_dev.conn = self.ssh_obj
                else:
                    logger.info(f"Recovered test device {dev_name} mounted")
                    return False
            else:
                logger.error(f"Recovered test device {dev_name} does not exist")
                return False

        test_devices = list(self.nvme_test_device.keys())
        logger.info(f"Successfully recovered test devices: {test_devices}")

        return True

    def get_recovery_file_name(self, recovery_data: dict):
        file_name = recovery_data["file_name"]
        magic_num = recovery_data["magic_number"]
        dir_name = recovery_data["dir_name"]

        file_name = f"_{magic_num}.".join(file_name.split("."))

        return f"{dir_name}/{file_name}"

    def remove_recovery_file(self, file_name):
        if not path.exists(file_name):
            logger.error(f"Recovery File {file_name} does not exist")
            return False

        os.remove(file_name)
        return True

    def prepare(self, hetero_setup_data: dict) -> bool:
        """ """
        self.hetero_setup_data = hetero_setup_data
        logger.info(self.hetero_setup_data)

        prepare_setup = True if hetero_setup_data["enable"] == "true" else False
        nr_device = int(hetero_setup_data["num_test_device"])
        config_data = hetero_setup_data["test_devices"]
        recovery_data = hetero_setup_data["recovery"]

        if not prepare_setup:
            logger.warning("Hetero device setup creation is disabled")
            return True

        recovery_file = self.get_recovery_file_name(recovery_data)

        # Select the minimum from the config
        end = len(config_data) if nr_device > len(config_data) else nr_device

        nvme_dev_list = [dev["dev_name"] for dev in hetero_setup_data["test_devices"]]
        if not self.load_test_devices(nvme_dev_list[:end], recovery_file):
            return False

        for index in range(end):
            dev_config = config_data[index]
            dev_name = dev_config["dev_name"]
            dev = self.nvme_test_device.get(dev_name, None)
            if not dev:
                logger.error(f"Failed to get the test device {dev_name}")
                return False

            if not dev.cleanup_ns():
                logger.error(f"Failed to clean namespace for device {dev_name}")
                return False

            if not dev.setup_ns(ns_config_list=dev_config["ns_config"]):
                logger.error(f"Failed to setup namespace for device {dev_name}")
                return False

        display_message("successfully created the pos hetero device setup")
        return True

    def reset(self, hetero_config, remove_recovery_file=False):
        hetero_config = hetero_config or self.hetero_setup_data
        if hetero_config["enable"] == "false":
            logger.info(
                "Hetero device setup creation was disabled. "
                "Setup reset is not required."
            )
            return True

        logger.info("Hetero setup enabled")
        if not self._do_spdk_setup_reset():
            logger.warning("Failed to reset nvme device binding")

        recovery_data = hetero_config["recovery"]
        recovery_file = self.get_recovery_file_name(recovery_data)

        if not self.recover_test_devices(recovery_file):
            logger.error("Failed to recover test devices")
            return False

        reset_error = []
        for dev_name, dev in self.nvme_test_device.items():
            if not dev.restore():
                reset_error.append(dev_name)

        if reset_error:
            logger.error(f"Failed to reset following devices: {reset_error}")
            return False

        if remove_recovery_file:
            logger.info(f"Delete Recovery File {recovery_file}")
            self.remove_recovery_file(recovery_file)

        display_message("Successfuly reset all nvme devices")
        return True


if __name__ == "__main__":
    from pos import POS

    pos = POS()

    tgt_setup_file = "hetero_setup.json"
    conf_dir = "/root/nehal/trident/testcase/config_files/"

    data_path = f"{conf_dir}{tgt_setup_file}"
    tgt_conf_data = pos._json_reader(data_path, abs_path=True)[1]

    print(tgt_conf_data)
    tgt_setup = TargetHeteroSetup(pos.target_ssh_obj, tgt_conf_data)

    test_devic = ["nvme0", "nvme1"]

    # assert tgt_setup.load_test_devices(test_devic)
    # assert tgt_setup.recover_test_devices()
    # assert tgt_setup.prepare(tgt_conf_data)
    assert tgt_setup.reset(tgt_conf_data)
