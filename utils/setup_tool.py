import sys
import os
import time
import json
import argparse
import re
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
from functools import reduce
from node import SSHclient
from pos import POS
import logger as logger

logger = logger.get_logger(__name__)

parser = argparse.ArgumentParser(description="Help desc for setup config tool")
parser.add_argument(
    "--all", action="store_true", help="runs all the requrirements in setup config tool"
)
parser.add_argument(
    "--verify_ssh",
    action="store_true",
    help="this option will verify the connectivity of ip addresses given in topology file",
)
parser.add_argument(
    "--verify_kernel",
    action="store_true",
    help="this option will verifies whether kernel version matches or not ",
)
parser.add_argument(
    "--verify_ssd",
    action="store_true",
    help="this option will verify whether the connected nvme devices are capable to run ibof os",
)
parser.add_argument(
    "--verify_data_ip",
    action="store_true",
    help="this option will give the connected mellanox interface ip addresses",
)
args = parser.parse_args()


class setup_config_tool:
    def __init__(self, config_dict):
        self.summary = []
        self.tar_ip = config_dict["login"]["target"]["server"][0]["ip"]
        self.tar_user = config_dict["login"]["target"]["server"][0]["username"]
        self.tar_passwd = config_dict["login"]["target"]["server"][0]["password"]
        client_count = config_dict["login"]["initiator"]["number"]
        self.init_ip = config_dict["login"]["initiator"]["client"][client_count]["ip"]
        self.init_user = config_dict["login"]["initiator"]["client"][client_count][
            "username"
        ]
        self.init_passwd = config_dict["login"]["initiator"]["client"][client_count][
            "password"
        ]
        self.pos_path = config_dict["login"]["paths"]["pos_path"]
        self.tar_mlnx_ip = config_dict["login"]["target"]["server"][0]["Data_Ip"]
        self.init_mlnx_ip = config_dict["login"]["initiator"]["client"][client_count][
            "Data_Ip"
        ]

    def Validate_IP(self, IP):
        regex = "^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"
        regex1 = "((([0-9a-fA-F]){1,4})\\:){7}([0-9a-fA-F]){1,4}"
        p = re.compile(regex)
        p1 = re.compile(regex1)
        if re.search(p, IP):
            return True, "Valid IPv4"
        elif re.search(p1, IP):
            return True, "Valid IPv6"
        return False, "Invalid IP"

    def Validate_ping(self, IP):
        ping_cmd = "ping -c 5 {}".format(IP)
        ping_out = subprocess.Popen([ping_cmd], stdout=subprocess.PIPE, shell=True)
        out = ping_out.communicate()
        if not "100% packet loss" in str(out):
            msg = "ping is successfull for the Ip Address {}".format(IP)
            return True, msg
        else:
            msg = "ping failed for the Ip address {} ... pls verify the IP".format(IP)
            return False, msg

    def verify_ssh(self):
        try:
            self.tar_ssh_obj = SSHclient(
                hostname=self.tar_ip, username=self.tar_user, password=self.tar_passwd
            )
        except:
            self.tar_ssh_obj = None
            pass
        if not self.tar_ssh_obj:
            tar_val_ip = self.Validate_IP(IP=self.tar_ip)
            if tar_val_ip[0] == True and tar_val_ip[1] == "Valid IPv4":
                tar_val_su = "Target {} is a valid IP address".format(self.tar_ip)
                self.summary.append(tar_val_su)
            if tar_val_ip[0] == True and tar_val_ip[1] == "Valid IPv6":
                tar_val_su_1 = "IPv6 address {} is not supported".format(self.tar_ip)
                self.summary.append(tar_val_su_1)
            if tar_val_ip[0] == False and tar_val_ip[1] == "Invalid IP":
                tar_val_su_1 = "Given IP address {} is not invalid and it is not IPv4 range".format(
                    self.tar_ip
                )
                self.summary.append(tar_val_su_1)
            ping = self.Validate_ping(IP=self.tar_ip)
            if ping[0] == True:
                self.summary.append(ping[1])
            else:
                self.summary.append(ping[1])
            self.tar_ssh_summary = (
                "Failed to take ssh for the target: {}  machine".format(self.tar_ip)
            )
            self.summary.append(self.tar_ssh_summary)
        else:
            self.tar_ssh_summary = (
                "Successfully taken ssh for the target: {}  machine".format(self.tar_ip)
            )
            self.summary.append(self.tar_ssh_summary)
        try:
            self.init_ssh_obj = SSHclient(
                hostname=self.init_ip,
                username=self.init_user,
                password=self.init_passwd,
            )
        except:
            self.init_ssh_obj = None
            pass
        if not self.init_ssh_obj:
            init_val_ip = self.Validate_IP(IP=self.init_ip)
            if init_val_ip[0] == True and init_val_ip[1] == "Valid IPv4":
                init_val_su = "Initiator {} is a valid IP address".format(self.init_ip)
                self.summary.append(init_val_su)
            if init_val_ip[0] == True and init_val_ip[1] == "Valid IPv6":
                init_val_su_1 = "IPv6 address {} is not supported".format(self.init_ip)
                self.summary.append(init_val_su_1)
            if init_val_ip[0] == False and init_val_ip[1] == "Invalid IP":
                init_val_su_2 = "Given IP address {} is not invalid and it is not IPv4 range".format(
                    self.init_ip
                )
                self.summary.append(init_val_su_2)
            ping = self.Validate_ping(IP=self.init_ip)
            if ping[0] == True:
                self.summary.append(ping[1])
            else:
                self.summary.append(ping[1])
            self.init_ssh_summary = (
                "Failed to take ssh for the initiator: {} machine".format(self.init_ip)
            )
            self.summary.append(self.init_ssh_summary)
        else:
            self.init_ssh_summary = (
                "Successfully taken ssh for the initiator : {}  machine".format(
                    self.init_ip
                )
            )
            self.summary.append(self.init_ssh_summary)
        if self.init_ssh_obj and self.tar_ssh_obj:
            return True
        else:
            return False

    def check_nvme_ssd(self):
        try:
            self.tar_ssh_obj = SSHclient(
                hostname=self.tar_ip, username=self.tar_user, password=self.tar_passwd
            )
        except:
            self.tar_ssh_obj = None
            pass
        if not self.tar_ssh_obj:
            ssd_ssh_summary = "Failed to take ssh for the machine: {} ... couldn't proceed further to check the ssd's".format(
                self.tar_ip
            )
            self.summary.append(ssd_ssh_summary)
            return False
        nvme_cnt = self.tar_ssh_obj.execute(
            "lspci -D | grep 'Non-V' | awk '{print $1}'"
        )
        if len(nvme_cnt) < 3:
            cnt_ssd_summary = "required number of ssd's are not there to start POS"
            self.summary.append(cnt_ssd_summary)
            flag_1 = False
            return False
        flag_1 = True
        reset_cmd = "{}/lib/spdk/scripts/setup.sh reset".format(self.pos_path)
        self.tar_ssh_obj.execute(reset_cmd)
        time.sleep(5)
        size_cmd = "lsblk -o NAME,SIZE | grep 'nvme' |  awk '{print $2}'"
        size_out = self.tar_ssh_obj.execute(size_cmd)
        if len(list(set(size_out))) > 10:
            size_summary = "Different size nvme devices exists ... "
            self.summary.append(size_summary)
            flag_3 = True
            return True
        flag_3 = True
        dev_cmd = "nvme list | grep 'nvme' | awk '{print $1}'"
        dev_list = self.tar_ssh_obj.execute(dev_cmd)
        for dev in dev_list:
            bs_cmd = "nvme id-ns {} -H | grep '(in use)' | awk '{{print $12}}'".format(
                dev.strip()
            )
            bs_out = self.tar_ssh_obj.execute(bs_cmd)
            if int(bs_out[0].strip()) != 512:
                bs_summary = f"device {dev.strip()} is having a block size of { bs_out[0].strip()}B which is not supported by pos ..."
                self.summary.append(bs_summary)
                flag_4 = True
                return True
        flag_4 = True
        if flag_1 and flag_3 and flag_4:
            self.ssd_summary = (
                "All the connected nvme devices satisfies the POS requirements"
            )
            self.summary.append(self.ssd_summary)

    def verify_kernel_version(self):
        try:
            self.tar_ssh_obj = SSHclient(
                hostname=self.tar_ip, username=self.tar_user, password=self.tar_passwd
            )
        except:
            self.tar_ssh_obj = None
            pass
        if not self.tar_ssh_obj:
            ssh_krnl_summary = "Failed to take ssh for the machine: {} ... couldn't proceed further to test the kernel version of target machine ".format(
                self.tar_ip
            )
            self.summary.append(ssh_krnl_summary)
            return False
        try:
            self.init_ssh_obj = SSHclient(
                hostname=self.init_ip,
                username=self.init_user,
                password=self.init_passwd,
            )
        except:
            self.init_ssh_obj = None
            pass
        if not self.init_ssh_obj:
            ssh_krnl_summary_1 = "Failed to take ssh for the machine: {} ... couldn't proceed to further to test the kernel version of initiator machine".format(
                self.init_ip
            )
            self.summary.append(ssh_krnl_summary_1)
            return False
        req_krnl_ver = "5.3.0"
        config_ver_sum = reduce(
            lambda x, y: int(x) + int(y), req_krnl_ver.split(".")[0:2]
        )
        if self.tar_ssh_obj:
            tar_ver = self.tar_ssh_obj.execute("uname -r ")
            target_kernel_version = tar_ver[0].strip().split("-")[0]
            tar_version_sum = reduce(
                lambda x, y: int(x) + int(y), target_kernel_version.split(".")[0:2]
            )
            if tar_version_sum >= config_ver_sum:
                tar_krnl_msg = (
                    "kernel version requirement satisfied on target machine {}".format(
                        self.tar_ip
                    )
                )
                self.summary.append(tar_krnl_msg)
            else:
                tar_krnl_msg = "kernel version requirement not satisfied on target machine {}... please install 5.0 above kernel ".format(
                    self.tar_ip
                )
                self.summary.append(tar_krnl_msg)
        if self.init_ssh_obj:
            init_ver = self.init_ssh_obj.execute("uname -r ")
            init_kernel_version = init_ver[0].strip().split("-")[0]
            init_version_sum = reduce(
                lambda x, y: int(x) + int(y), init_kernel_version.split(".")[0:2]
            )
            if init_version_sum >= config_ver_sum:
                init_krnl_msg = "kernel version requirement satisfied on initiator machine {}".format(
                    self.init_ip
                )
                self.summary.append(init_krnl_msg)
            else:
                tar_krnl_msg = "kernel version requirement not satisfied on initiator machine {}... please install 5.0 above kernel ".format(
                    self.init_ip
                )
                self.summary.append(init_krnl_msg)

    def verify_data_ip_ping(self):
        try:
            self.tar_ssh_obj = SSHclient(
                hostname=self.tar_ip, username=self.tar_user, password=self.tar_passwd
            )
        except:
            self.tar_ssh_obj = None
            pass
        if not self.tar_ssh_obj:
            ssh_ping_summary = "Failed to take ssh for the machine: {} ... couldn't proceed further to test the data ip ping ".format(
                self.tar_ip
            )
            self.summary.append(ssh_ping_summary)
            return False
        try:
            self.init_ssh_obj = SSHclient(
                hostname=self.init_ip,
                username=self.init_user,
                password=self.init_passwd,
            )
        except:
            self.init_ssh_obj = None
            pass
        if not self.init_ssh_obj:
            ssh_ping_summary_1 = "Failed to take ssh for the machine: {} ... couldn't proceed to further to test the data ip ping".format(
                self.init_ip
            )
            self.summary.append(ssh_ping_summary_1)
            return False
        tcp = set(["tcp", "t"])
        while True:
            choice = "tcp"
            if choice in tcp:
                out = self.tar_ssh_obj.execute(
                    "ping -c 5 {} ".format(self.init_mlnx_ip)
                )
                output_1 = "\n".join(out)
                if "0% packet loss" in output_1:
                    flag_1 = True
                else:
                    tcp_ping_summary = "ping to initiator data ip {} failed from target machine {}".format(
                        self.init_mlnx_ip, self.tar_ip
                    )
                    self.summary.append(tcp_ping_summary)
                    return False
                self.init_ssh_obj.execute("modprobe nvme_tcp")
                out = self.init_ssh_obj.execute(
                    "ping -c 5 {} ".format(self.tar_mlnx_ip)
                )
                output_2 = "\n".join(out)
                if "0% packet loss" in output_2:
                    flag_2 = True
                else:
                    tcp_ping_summary_1 = "ping to target data ip {} failed from initaiator machine {}".format(
                        self.tar_mlnx_ip, self.init_ip
                    )
                    self.summary.append(tcp_ping_summary_1)
                    return False
                if flag_1 and flag_2:
                    tot_tcp_summary = (
                        "TCP : data ip ping is successfull b/w initiator & target"
                    )
                    self.summary.append(tot_tcp_summary)
                    break

    def usermode_prep(self):
        user_mode = f"{self.pos_path}/script/setup_env.sh"
        self.tar_ssh_obj = SSHclient(
            hostname=self.tar_ip, username=self.tar_user, password=self.tar_passwd
        )
        self.tar_ssh_obj.execute(user_mode)


def main():
    flag = False
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open("{}/../testcase/config_files/topology.json".format(dir_path)) as f:
        config_dict = json.load(f)
    obj = setup_config_tool(config_dict)
    if args.all:
        flag = True
        out = obj.verify_ssh()
        krnl = obj.verify_kernel_version()
        ret = obj.check_nvme_ssd()
        ping_out = obj.verify_data_ip_ping()
    if args.verify_ssh:
        flag = True
        obj.verify_ssh()
    if args.verify_kernel:
        flag = True
        obj.verify_kernel_version()
    if args.verify_ssd:
        flag = True
        obj.check_nvme_ssd()
    if args.verify_data_ip:
        flag = True
        ping_out = obj.verify_data_ip_ping()
    obj.usermode_prep()
    if flag == True:
        print(":::::::::::::::::Summary of the result is #:::::::::::: ")
        print(*obj.summary, sep="\n")
        print("::::::::::::::::::::::::::::::::::::::::::::::::::::::: ")


if __name__ == "__main__":
    main()
