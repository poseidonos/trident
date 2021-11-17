import json, time, math, re, string, random
import logger
from utils import Client
from cli import Cli
from datetime import datetime, timedelta

logger = logger.get_logger(__name__)


class TargetUtils:
    def __init__(
        self,
        ssh_obj: "ssh_obj of host",
        pos_path: "path of POS code",
        array_name: str = "POS_ARRAY1",
    ):
        self.cli = Cli(ssh_obj, pos_path, array_name)
        self.ssh_obj = ssh_obj
        self.array_name = array_name

    def create_mount_multiple(
        self,
        array_name="POS_ARRAY1",
        size=None,
        volname="pos_vol",
        num_vols=10,
        iops=1000000,
        bw=10000,
        nqn=None,
    ) -> bool:
        """
        Method to create and mount multiple volumes
        """
        try:
            out = self.cli.info_array(array_name)
            temp = self.convert_size(out[1]["capacity"]).split(" ")
            if "TB" in temp:
                size_params = int(float(temp[0]) * 1000)
                size_per_vol = int(size_params / num_vols)
                d_size = str(size_per_vol) + "GB"

            for numvol in range(num_vols):
                volume_name = volname + str(numvol)
                self.cli.create_volume(volume_name, d_size, array_name, iops=iops, bw=bw)
                self.cli.mount_volume(volume_name, array_name, nqn=nqn)
            return True
        except Exception as e:
            logger.error(e)

    def generate_nqn_name(self, default_nqn_name: str = "nqn.2021-10.pos") -> str:
        """
        Method to generate nqn name
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

    def dev_bdf_map(self) -> (bool, dict()):
        """
        Method to get device address
        """
        try:
            dev_bdf_map = {}
            list_dev_out = self.cli.list_device()
            if len(list_dev_out) == 0:
                raise Exception("No Devices found")
            for dev in list_dev_out[3]:
                dev_bdf_map[dev] = list_dev_out[3][dev]["addr"]
                logger.info(dev_bdf_map)
        except Exception as e:
            logger.error("Execution failed with exception {}".format(e))
            return False, None
        return True, dev_bdf_map

    def get_devs(self, prop={"type": "SSD"}) -> (bool, dict()):
        """
        Method to get devices
        """
        dev_map = self.cli.list_device()[3]
        devs = [k for k, v in dev_map.items() if prop.items() <= v.items()]
        return devs

    def device_hot_remove(self, device_list: list) -> (bool):
        """
        Method to hot remove devices
        """
        try:
            self.dev_addr = []
            dev_list = self.get_devs()
            for each_dev in device_list:
                if each_dev not in dev_list:
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
                        "failed to hot plug the device {}verifing in list_dev ".format(
                            dev
                        )
                    )
                    out = self.list_dev()
                    if dev in out[3]:
                        logger.error("failed to remove devie")
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
        """
        try:
            logger.info("Executing list dev command before rescan")
            list_dev_out_bfr_rescan = self.dev_bdf_map()
            logger.info(
                "No. of devices before rescan: {} ".format(
                    len(list_dev_out_bfr_rescan[1])
                )
            )
            logger.info("running pci rescan command ")
            re_scan_cmd = "echo 1 > /sys/bus/pci/rescan "
            self.ssh_obj.execute(re_scan_cmd)
            logger.info("verifying whether the removed device is attached back or not")
            logger.info("scanning the devices after rescan")
            time.sleep(5)  # Adding 5 sec sleep for the sys to get back in normal state
            scan_out = self.scan_dev()
            if scan_out[0] == False:
                logger.error("after pci rescan scan_dev command failed ")
                return False
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
            return False, None

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

    def get_mellanox_interface_ip(self) -> str:
        """
        Method to get mellanox interface ip
        """
        try:
            mlx_inter = []

            self.cnctd_mlx_inter = []

            ip_addr = []

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
                        ip_addr.append(ip_address)
                except:
                    logger.warn(
                        "IP is not assigned to the connected mellanox interface {} ".format(
                            c_iner.strip()
                        )
                    )
            logger.info("Mellanox interfaces are {} ".format(mlx_inter))
            logger.info(
                "Connected Mellanox interfaces are {} ".format(self.cnctd_mlx_inter)
            )
            if len(ip_addr) == 0:
                raise Exception("Ip is not assigned to any of the Mellanox")
        except Exception as e:
            logger.error("Get_mel_IP failed due to {}".format(e))
            return (False, None)
        return (True, ip_addr)

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

    def udev_install(self) -> bool:
        """
        Method to udev install
        """
        try:
            logger.info("Running udev_install command")
            cmd = "cd {} ; make udev_install ".format(self.pos_path)
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

    def setup_env_pos(self) -> bool:
        """
        Method to setup poseidon envoirment
        """
        try:
            cmd = "{}/script/setup_env.sh".format(self.pos_path)
            out = self.ssh_obj.execute(cmd)
            if "Setup env. done" in out[-1]:
                logger.info("Bringing drives from kernel mode to user mode successfull")
                return True
        except Exception as e:
            logger.error("Execution  failed because of {}".format(e))
            return False

    def spor_prep(self) -> bool:
        """
        Method to spor preparation
        """
        try:
            self.wbt_flush_gcov()
            self.stop_pos()
            self.ssh_obj.execute(
                "{}/script/backup_latest_hugepages_for_uram.sh".format(self.pos_path),
                get_pty=True,
            )
            self.ssh_obj.execute("rm -fr /dev/shm/ibof*", get_pty=True)

        except Exception as e:
            logger.error(e)
            return False

    def check_rebuild_status(self, array_name: str = None) -> (bool):
        """
        Method to check rebuild status
        """
        try:
            if array_name == None:
                array_name = self.array_name
            info_status = 0
            while info_status <= 300:
                get_pos_status = self.cli.info_array(array_name=array_name)
                if get_pos_status[0] == True and get_pos_status[3] == "NORMAL":
                    logger.info("rebuild status is updated in array info command")
                    break
                else:
                    info_status += 1
                    logger.info("verifying if rebuilding progress status is 0")
                    time.sleep(2)
            else:
                raise Exception("rebuilding failed for the array {}".format(array_name))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False
        return True

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

    def random_File_name(self) -> str:
        """
        Method to generate random file name
        """
        letters = string.ascii_lowercase
        Name = "".join(random.choice(letters) for i in range(15))
        datetime_object = datetime.now()
        date = (str(datetime_object).replace(" ", "-")).split(".")[0].replace(":", "-")

        return Name + "_" + date
