#!/usr/bin/python
# Script for parsing output of lshw and hostnamectl and generate environmental tags in dictionary format
import sys
import logger
import pytest
from collections import OrderedDict
from lxml import etree
from subprocess import Popen, PIPE

# from hurry.filesize import size

sys.path.insert(0, "../")
from node import SSHclient

logger = logger.get_logger(__name__)


class EnvTags(SSHclient):
    def __init__(self, item, ip, username, password):
        self.item = item
        self.ip = ip
        self.username = username
        self.password = password
        self.inv = OrderedDict()
        try:
            self.conn = SSHclient(ip, username, password)
        except Exception as e:
            logger.error("Unable to connect to {} due to {}".format(self.item, e))
            assert 0

    def get_tags(self):
        try:
            logger.info(
                "Running command 'lshw -xml -numeric' in the node : {}".format(
                    self.item[0]
                )
            )
            inventory = self.conn.execute("lshw -xml -numeric")
            inventory = "\n".join(inventory)
            inventory = etree.XML(inventory)

            find_system = etree.XPath(".//node[@class='system']")
            for sys in find_system(inventory):
                self.inv["System Model"] = sys.find("product").text
                self.inv["System Vendor"] = sys.find("vendor").text
                try:
                    self.inv["System Serial Number"] = sys.find("serial").text
                except Exception as e:
                    logger.info(
                        "No serial number found for the node : {}".format(self.item)
                    )
                    self.inv["System Serial Number"] = "Nil"
            find_bus = etree.XPath(".//node[@class='bus']")
            for bus in find_bus(inventory):
                if (
                    bus.find("description") is not None
                    and bus.find("description").text == "Motherboard"
                ):
                    try:
                        self.inv["Motherboard Model"] = bus.find("product").text
                    except Exception as e:
                        logger.info(
                            "No Motherboard Model found for the node : {}".format(
                                self.item
                            )
                        )
                        self.inv["Motherboard Model"] = "Nil"
                    try:
                        self.inv["Motherboard vendor"] = bus.find("vendor").text
                    except Exception as e:
                        logger.info(
                            "No Motherboard Vendor found for the node : {}".format(
                                self.item
                            )
                        )
                        self.inv["Motherboard vendor"] = "Nil"
                    try:
                        self.inv["Motherboard Serial Number"] = bus.find("serial").text
                    except Exception as e:
                        logger.info(
                            "No Motherboard Serial Number found for the node : {}".format(
                                self.item
                            )
                        )
                        self.inv["Motherboard Serial Number"] = "Nil"

            find_memory = etree.XPath(".//node[@class='memory']")
            for mem in find_memory(inventory):
                if (
                    mem.find("description") is not None
                    and mem.find("description").text == "BIOS"
                ):
                    self.inv["System BIOS"] = mem.find("vendor").text
                    self.inv["System BIOS Version"] = mem.find("version").text
                    self.inv["System BIOS Date"] = mem.find("date").text

            find_cpus = etree.XPath(".//node[@class='processor']")
            self.inv["Processsor Model"] = find_cpus(inventory)[0].find("product").text
            self.inv["Processsor Vendor"] = find_cpus(inventory)[0].find("vendor").text
            self.inv["Processor Sockets"] = len(find_cpus(inventory))
            self.inv["Processor Cores Per Socket"] = (
                find_cpus(inventory)[0]
                .find('configuration/setting/[@id="cores"]')
                .get("value")
            )

            total_mem = 0
            for mem in find_memory(inventory):
                if mem.find("size") is not None:
                    total_mem = total_mem + int(mem.find("size").text)
                    self.inv["Total Memory"] = total_mem

            find_disks = etree.XPath(".//node[@class='disk']")
            numdisks = 0
            diskspace = 0
            for disk in find_disks(inventory):
                if disk.find("size") is not None:
                    numdisks = numdisks + 1
                    diskspace = diskspace + int(disk.find("size").text)
                    self.inv["Device" + str(numdisks)] = (
                        disk.find("description").text
                        + "_"
                        + disk.find("product").text
                        + "_"
                        + disk.find("logicalname").text
                    )
            find_networks = etree.XPath(".//node[@class='network']")
            num_net = 0
            for net in find_networks(inventory):
                if net.find("product") is not None and net.find("vendor") is not None:
                    num_net += 1
                    self.inv["Network Interface" + str(num_net)] = (
                        net.find("description").text
                        + "_"
                        + net.find("product").text
                        + "_"
                        + net.find("vendor").text
                    )

            logger.info(
                "Runnning command 'hostnamectl | grep 'Static hostname'' in the remote system"
            )
            inventory = self.conn.execute("hostnamectl | grep 'Static hostname'")
            self.inv["Host Name"] = inventory[0].split("Static hostname:", 1)[1].strip()
            logger.info(
                "Runnning command 'hostnamectl | grep 'Operating System'' in the remote system"
            )
            inventory = self.conn.execute("hostnamectl | grep 'Operating System'")
            self.inv["Operating System"] = (
                inventory[0].split("Operating System:", 1)[1].strip()
            )
            logger.info(
                "Runnning command 'hostnamectl | grep 'Kernel'' in the remote system"
            )
            inventory = self.conn.execute("hostnamectl | grep 'Kernel'")
            self.inv["Kernel"] = inventory[0].split("Kernel:", 1)[1].strip()
            return True
        except Exception as e:
            logger.error(
                "lshw command execution on node {} failed due to: {}".format(
                    self.item[0], e
                )
            )
            return False
