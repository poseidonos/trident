from curses.ascii import ctrl
from enum import Enum
import inspect
import json
from os import path
import pathlib
import re

import logger

logger = logger.get_logger(__name__)

class NS_State(Enum):
    UNKNOWN = 0
    ACTIVE = 1
    INACTIVE = 2
    ALLOCATED = 3
    UNALLOCATED = 4

class NVMe_Command:
    def __init__(self, conn: object) -> None:
        '''
        conn : Connection Object
        '''
        self.conn = conn        # SSH Connection Object
        pass

    def nvme_submit(self, command: str, json_out: bool=True) -> bool:
        '''
        command: nvme cli command
        '''
        command = f"nvme {command}"
        if json_out:
            command += " -o json"

        out = self.conn.execute(command)
        # TODO fix execute api
        try:
            out = "".join(out)
        except:
            out = "".join(out[0])

        if 'No such file or directory' in out:
            logger.error(f"{out}")
            return False

        self.response = "".join(out)
        return True

    def identify_controller(self, nvme_dev: str, json_out: bool=True) -> bool:
        '''
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        '''
        id_ctrl_cmd = f"id-ctrl {nvme_dev}"
 
        if self.nvme_submit(id_ctrl_cmd, json_out):
            self.id_ctrl = self.response
        else:
            logger.error(f"Identify controller command failed")
            return False

        return True

    def indentify_ns(self, nvme_dev: str, nsid: int=1, json_out: bool=True) -> bool:
        '''
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        '''
        id_ns_cmd = f"id-ns {nvme_dev} -n {nsid}"

        if self.nvme_submit(id_ns_cmd, json_out):
            self.id_ns = self.response
        else:
            logger.error(f"Identify namespace command failed")
            return False

        return True

    def list_ns(self, nvme_dev: str, nsid: int=None) -> bool:
        '''
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        '''
        list_ns_cmd = f"list-ns {nvme_dev}"

        if nsid != None:
            list_ns_cmd += f" -n {nsid}"

        if self.nvme_submit(list_ns_cmd, json_out=False):
            self.ns_list = self.response
        else:
            logger.error(f"List namespace command failed")
            return False

        return True

    def list_ctrl(self, nvme_dev: str, nsid: int=None) -> bool:
        '''
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        '''
        list_ctrl_cmd = f"list-ctrl {nvme_dev}"

        if nsid != None:
            list_ctrl_cmd += f" -n {nsid}"

        if self.nvme_submit(list_ctrl_cmd, json_out=False):
            self.ctrl_list = self.response
        else:
            logger.error(f"List controller command failed")
            return False

        return True

    def attach_detach_ns(self, attach: bool, nvme_dev: str, nsid: int, ctrl_id: int) -> bool:
        '''
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        ctrl_id: Controller ID
        '''
        if attach:
            attach_detach = "attach"
        else:
            attach_detach = 'detach'

        cmd = f"{attach_detach}-ns {nvme_dev} -n {nsid} -c {ctrl_id}"

        if self.nvme_submit(cmd, json_out=False):
            if f"{attach_detach}-ns: Success, nsid:{nsid}" in self.response:
                return True
        
        logger.error(f"{attach_detach.title()} Namespace command failed")
        return False

    def delete_ns(self, nvme_dev: str, nsid: int) -> bool:
        '''       
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        '''
        delete_ns_cmd = f"delete-ns {nvme_dev} -n {nsid}"
        
        if self.nvme_submit(delete_ns_cmd, json_out=False):
            if f"delete-ns: Success, deleted nsid:{nsid}" in self.response:
                return True

        logger.error(f"Delete Namespace command failed")
        return False

    def create_ns(self, nvme_dev: str, size: int, flbas: int) -> bool:
        '''
        nvme_dev: Name of nvme device. i.e: /dev/nvme0
        nsid: Namespace ID
        
        '''
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

        if self.nvme_submit(list_nvme_cmd, json_out=False):
            self.list_nvme = self.response
            return True

        logger.error(f"List NVMe command failed")
        return False


class NVMe_Dev(NVMe_Command):
    def __init__(self, ssh_obj: object, name: str, serial_number: str=None, bdf: str=None) -> None:
        self.conn = ssh_obj
        self.name = name
        #self.sn = serial_number
        #self.bdf = bdf
        self.removed = False
        self.kernal_mapped = True           # Mark true when device is mapped with kernel space
        self.nss = []                       # List of Namespace Objects
        self.ctrl = None                    # Controller Object
        self.nss_org = []                   # Store Namespace Original Config
        self.ns_created = False             # Mark true when new NS are created
        self.ns_deleted = False             # Mark true when existing NS are deleted
        self.ns_restored = False            # Mark true when drive original status is restored

    class Namespace:
        def __init__(self, nsid: int, size: int=0, state: str=NS_State.UNKNOWN) -> None:
            self.nsid = nsid                # Namespace ID
            self.size = size                # Namespace Size
            self.state = state              # Namespace State
            self.nlbaf = None               # Number of LBA format
            self.flbas = None               # Selected LBA Format
            self.lba_format = {}            # LBA Format Decode
            self.lba_format['metadata'] = 0     # Metadata Size in Bytes
            self.lba_format['data'] = 0         # Data Size in Bytes
            self.ctrl_list = []             # Attached Controller

        def __str__(self) -> str:
            return  f"\nNamespace Id    : {self.nsid} "\
                    f"\nNS Size         : {self.size} "\
                    f"\nNS State        : {self.state} "\
                    f"\nNr of Formats   : {self.nlbaf} "\
                    f"\nLBA Format      : {self.lba_format} "\
                    f"\nAttached Ctrl   : {self.ctrl_list} "

    class Controller:
        def __init__(self, cntlid: int=0) -> None:
            self.controller_id = cntlid         # Controller Id 
            self.serial_number = None           # Controller Serial Number
            self.total_nvm_cap = 0              # Total NVM Capacity
            self.num_namespace = 0              # Max Number of Namespace
            self.ns_mgt_supported = False       # NS Management and Attachment Supported
            self.ns_fmt_supported = False       # Format NVM Supported

        def __str__(self) -> str:
            return  f"\nController Id      : {self.controller_id} "\
                    f"\nSerial Number      : {self.serial_number} "\
                    f"\nNVM Capacity       : {self.total_nvm_cap} "\
                    f"\nNumber Of NS       : {self.num_namespace} "\
                    f"\nNS Mgmt Supported  : {self.ns_mgt_supported} "\
                    f"\nFormat Supported   : {self.ns_fmt_supported} "

    def load_info(self) -> bool:
        # Issue Identify Controller
        nvme_dev = self.name
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
        logger.info(f"Controller Info: {ctrl}")

        if not self.list_ns(nvme_dev):
            logger.error("Failed to get active namespace list")
            return False
        
        nsid_list = re.findall('0x[\da-f]+', self.ns_list)
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
            ns.flbas = int(id_ns["flbas"]) & 0xf 
            ns.lba_format['metadata'] = int(id_ns["lbafs"][ns.flbas]["ms"])
            ns.lba_format['data'] = 2 ** int(id_ns["lbafs"][ns.flbas]["ds"])

            if not self.list_ctrl(nvme_dev):
                logger.error(f"Failed to get controller list")
                return False

            ctrl_list = re.findall('0x\d+', self.ctrl_list)
            ns.ctrl_list = list(map(lambda x: int(x, 0), ctrl_list))

            logger.info(f"Namespace Info: {ns}")
            self.nss.append(ns)


        if not self.nss_org:
            self.nss_org = self.nss[:]
                
        return True


    def print_info(self, all: bool=True) -> None:
        logger.info(f"{self.ctrl}")
        logger.info(f"{self.ns_list}")
        # Issue List Namespace
        # Issue Identify Namespace to all NS
        pass


    def restore(self) -> bool:
        '''
        
        '''
        nvme_dev = self.name
        if not self.ns_created and not self.ns_deleted:
            logger.info(f"Skipped! The drive {nvme_dev} is in original state")
            return True

        if self.nss:
            if not self.cleanup_ns():
                return False

        for ns_obj in self.nss_org:
            nsid = ns_obj.nsid
            logger.info(f"Restore namespace [nsid: {nsid}]")
            if not self.create_ns(nvme_dev=nvme_dev, size=ns_obj.size,
                                 flbas=ns_obj.flbas):
                logger.error(f"Failed to create ns[{nsid}]")
                return False
            if nsid != self.new_nsid:
                logger.warning(f"Created NSID[{self.new_nsid}] match failed")

            for ctrl_id in ns_obj.ctrl_list:
                # Attach NS
                if not self.attach_detach_ns(attach=True, nvme_dev=nvme_dev,
                                     nsid=self.new_nsid, ctrl_id=ctrl_id):
                    logger.error(f"Failed to attach ns[{self.new_nsid}] ctrl[{ctrl_id}]")
                    return False

        self.ns_restored = True
        self.ns_created = False
        self.ns_deleted = False
        return True

    def cleanup_ns(self) -> bool:
        nvme_dev = self.name
        while self.nss:
            ns_obj = self.nss[0]
            nsid = ns_obj.nsid
            for ctrl_id in ns_obj.ctrl_list:
                # Detach NS
                logger.info(f"Detach namespace [nsid: {nsid}]")
                if not self.attach_detach_ns(attach=False, nvme_dev=nvme_dev,
                                     nsid=nsid, ctrl_id=ctrl_id):
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
        '''
        ns_config: List of Dict of Namespace Config
                    [ { 'num_namespace': 1,
                        'ns_size': '19GiB',
                        'attach': True} ]
        
        '''
        nvme_dev = self.name
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
                if unit in ['gib', 'gb']:
                    size = size * 1024 * 1024 * 1024
                elif unit in ['tib', 'tb']:
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
                if not self.create_ns(nvme_dev=nvme_dev,
                                    size=size, flbas=flbas):
                    
                    logger.error("Failed to create namespace")
                    return False
                nsid = self.new_nsid
                ctrl_id = self.ctrl.controller_id

                ns_obj = self.Namespace(nsid=nsid)
                ns_obj.size = size
                ns_obj.state = NS_State.ALLOCATED
                ns_obj.flbas = flbas
                ns_obj.lba_format['metadata'] = 0
                ns_obj.lba_format['data'] = 512

                if ns_config.get('attach', True):
                    if not self.attach_detach_ns(attach=True, nvme_dev=nvme_dev,
                                                nsid=nsid, ctrl_id=ctrl_id):
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
    def __init__(self, ssh_obj: object, hetero_setup_data: dict=None) -> None:
        self.ssh_obj = ssh_obj
        self.hetero_setup_data = hetero_setup_data
        self.nvme_test_device = {}
        
    def load_test_devices(self, device_list: list) -> bool:
        '''
        device_list: i.e ['/dev/nvme0', '/dev/nvme1']
        '''
        error_dev = []
        for dev_name in device_list:
            nvme_dev = NVMe_Dev(ssh_obj=self.ssh_obj, name=dev_name)
            if nvme_dev.load_info():
                self.nvme_test_device[dev_name] = nvme_dev
            else:
                error_dev.append(nvme_dev)

        if error_dev:
            logger.error(f"Failed to load the following device: {error_dev}")
            return False

        return True


    def prepare(self, hetero_setup_data: dict) -> bool:
        '''
        
        '''
        nr_device = int(hetero_setup_data["num_test_device"])
        config_data = hetero_setup_data["test_devices"]

        # Select the minimum from the config
        end = len(config_data) if nr_device > len(config_data) else nr_device

        nvme_dev_list = [dev["dev_name"] for dev in hetero_setup_data["test_devices"]]
        if not self.load_test_devices(device_list=nvme_dev_list[:end]):
            return False
        
        for index in range(end):
            dev_config = config_data[index]
            dev_name = dev_config['dev_name']
            dev = self.nvme_test_device.get(dev_name, None)
            if not dev:
                logger.error(f"Failed to get the test device {dev_name}")
                return False

            if not dev.cleanup_ns():
                logger.error(f"Failed to clean namespace for device {dev_name}")
                return False

            if not dev.setup_ns(ns_config_list=dev_config['ns_config']):
                logger.error(f"Failed to setup namespace for device {dev_name}")
                return False
            
        logger.info("successfully created the pos hetero device setup")
        return True

    def reset(self):
        reset_error = []
        for dev_name, dev in self.nvme_test_device.items():
            if not dev.restore():
                reset_error.append(dev_name)

        if reset_error:
            logger.error(f"Failed to reset following devices: {reset_error}")
            return False
        
        logger.info("Successfuly reset all nvme devices")
        return True

if __name__ == '__main__':
    from pos import POS

    pos = POS()
    tgt_setup = TargetHeteroSetup(pos.target_ssh_obj)
    tgt_setup_file = "hetero_setup.json"
    conf_dir = "/root/nehal/trident/testcase/config_files/"

    data_path = f"{conf_dir}{tgt_setup_file}"
    tgt_conf_data = pos._json_reader(data_path, abs_path=True)[1]
    
    print(tgt_conf_data)

    
    tgt_setup.prepare(tgt_conf_data)
    tgt_setup.reset()
    


