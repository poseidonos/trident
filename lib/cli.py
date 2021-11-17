import json
import time
from datetime import timedelta
import logger
from utils import Client

logger = logger.get_logger(__name__)
# from target_utils import TargetUtils as target_utils


class Cli:
    def __init__(
        self,
        con: "node ssh object of the target",
        pos_path: "POS path",
        array_name="POS_ARRAY1",
    ):

        self.ssh_obj = con
        self.pos_path = pos_path
        self.array_name = array_name
        self.new_cli_path = "/bin/poseidonos-cli"
        self.cli_history = []

    def parse_out(
        self,
        jsonout: dict(),
        command: str,
    ) -> dict():
        """
        Method to parse JSON params of CLI
        """
        out = json.loads(jsonout)
        command = out["Response"]["command"]
        if "param" in out.keys():
            param = out["Request"]["param"]
        else:
            param = {}
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
        parse_out = {}
        if "data" in out["Response"]["result"]:
            parse_out = {
                "output": out,
                "command": command,
                "status_code": status_code,
                "description": description,
                "data": out["Response"]["result"]["data"],
                "params": param,
            }
        else:
            parse_out = {
                "output": out,
                "command": command,
                "status_code": status_code,
                "description": description,
                "params": param,
                "data" : {}
            }
        logger.info(parse_out)    
        self.add_cli_history(parse_out)
        return parse_out
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
    def run_cli_command(
        self, command: str, command_type="request", timeout=1800
    ) -> (bool, list):
        """
        Method to Execute CLIT commands and return Response
        """

        try:
            retry_cnt = 1
            cmd = "{}{} {} {} --json-res".format(
                self.pos_path, self.new_cli_path, command_type, command
            )
            start_time = time.time()
            run_end_time = start_time + timeout
            while time.time() < run_end_time:
                out = self.ssh_obj.execute(cmd, get_pty=True)
                logger.info(out)
                elapsed_time_secs = time.time() - start_time
                logger.info(
                    "command execution completed in  : {} secs ".format(
                        timedelta(seconds=elapsed_time_secs)
                    )
                )
                out = "".join(out)
                logger.info("Raw output of the command {} is {}".format(command, out))
                if "cannot connect to the PoseidonOS server" in out:
                    logger.warning("POSis not running! please start POS and try again!")
                    return False, out
                elif "invalid data metric" in out:
                    logger.warning("invalid syntax passed to the command ")
                    return False, out
                elif "invalid json file" in out:
                    logger.error("passed file contains invalid json data")
                    return False, out
                elif "Receiving error" in out:
                    logger.error("ibof os crashed in between ! please check ibof logs")
                    return False, out
                else:
                    parse_out = self.parse_out(out, command)
                    if parse_out["status_code"] == 0:
                        return True, parse_out
                    elif parse_out["status_code"] == 1030:
                        logger.info(
                            "Poseidonos is in Busy state, status code is {}. Command retry count is {}".format(
                                status_code, retry_cnt
                            )
                        )
                        retry_cnt += 1
                        time.sleep(5)
                        continue
                    else:
                        return False, out

        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            #out = self.ssh_obj.execute("pkill -9 pos")
            self.core_dump()
            return False, None

    def start_pos(self) -> bool:
        """
        Method to start pos
        """
        try:
            cli_error, jout = self.run_cli_command("start", "system")
            if cli_error == True:
                    return True
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def list_array(self) -> (bool, list, dict()):
        """
        Method to list array
        """
        try:
            array_dict = {}
            cmd = "list"
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                out = jout["output"]["Response"]
                if "There is no array" in out["result"]["data"]["arrayList"]:
                    logger.info("No arrays present in the config")
                    return True, out, array_dict
                else:
                    logger.info(out["result"]["data"]["arrayList"])
                    for i in out["result"]["data"]["arrayList"]:
                        a_name = i["name"]
                        a_status = i["status"]
                        array_dict[a_name] = a_status
                    logger.info(array_dict)
                    return True, out, array_dict
            else:
                raise Exception("list array command execution failed ")
        except Exception as e:
            logger.error("list array command failed with exception {}".format(e))
            return False, out

    def stop_pos(self, grace_shutdown=True, time_out=300) -> bool:
        """
        Method to stop poseidon
        """
        try:
            if grace_shutdown:
                ibof_info = self.list_array()
                if ibof_info[0] == True:
                    logger.info("successfully fetched the POS os info")

                    if len(list(ibof_info[2].keys())) == 0:
                        logger.info("no array present to unmount")
                    else:
                        for array in list(ibof_info[2].keys()):

                            self.array_name = array
                            if ibof_info[2][array]["status"] == "Mounted":
                                unmount_out = self.mount_unmount_array(
                                    operation="unmount"
                                )

                            self.delete_array()
                out = self.run_cli_command("stop --force", command_type="system")

                if out[0] == True:
                    if out[1]["output"]["Response"]["result"]["status"]["code"] == 0:
                        logger.info("POS was stopped successfully!!! verifying PID")
                        count = 0
                        while True:
                            pos_count = 0
                            process_out = self.ssh_obj.execute(
                                command="ps -eaf | grep 'poseidonos'"
                            )
                            logger.info(process_out)
                            for i in process_out:
                                logger.info(i)
                                if "poseidonos" in i:
                                    pos_count += 1
                            if pos_count > 0:
                                logger.warning("POS PID is still active")
                                time.sleep(10)
                                count += 10
                            else:
                                break
                            if count == time_out:
                                raise Exception("failed to kill pos")
            else:
                self.ssh_obj.execute(command="pkill -9 pos")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False
        return True

    def scan_device(
        self,
    ) -> dict():
        """
        Method to scan devices
        """
        try:
            cmd = "scan"
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def list_device(self) -> (bool, dict):
        """
        Method to list devices
        """
        try:
            cmd = "list"
            cli_error, out = self.run_cli_command(cmd, command_type="device")
            devices = []
            device_map = {}
            dev_type = {"NVRAM": [], "SSD": []}
            if cli_error == True:
                if out["status_code"] == 0:
                    if out["description"].lower() == "no any device exists":
                        logger.info("No devices listed")
                        return True, out, devices, device_map, dev_type
                    if "data" in out:
                        dev = out["data"]["devicelist"]
                        for device in dev:
                            devices.append(device["name"])
                            dev_map = {
                                "name": device["name"],
                                "addr": device["addr"],
                                "mn": device["mn"],
                                "sn": device["sn"],
                                "size": device["size"],
                                "type": device["type"],
                            }
                            if dev_map["type"] in dev_type.keys():
                                dev_type[dev_map["type"]].append(dev_map["name"])
                                device_map.update({device["name"]: dev_map})

                        return (
                            True,
                            out,
                            devices,
                            device_map,
                            dev_type["NVRAM"],
                            dev_type["SSD"],
                        )
                else:
                    raise Exception(
                        "list dev command failed with status code {}".format(
                            out["status_code"]
                        )
                    )
            else:
                raise Exception("list dev command failed with error {}".format(out))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, None, None, None, None

    def create_array(
        self,
        write_buffer: str = "uram0",
        data: str = "unvme-ns-0,unvme-ns-1,unvme-ns-2",
        spare: str = "unvme-ns-3",
        raid_type: str = "RAID5",
        array_name: str = None,
        npor=False,
    ) -> dict():
        """
        Method to create array
        """
        try:
            if array_name != None:
                self.array_name = array_name
            if npor == False:
                out = self.reset_devel()
            if spare:
                cmd = "create -b {} -d {} -s {} -a {} --raid {}".format(
                    write_buffer, data, spare, self.array_name, raid_type
                )
            else:
                cmd = "create -b {} -d {} -a {} --raid {}".format(
                    write_buffer, data, self.array_name, raid_type
                )
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def mount_array(self, array_name: str = None) -> dict():
        """
        Method to mount array
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "mount -a {}".format(self.array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return True
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def unmount_array(self, array_name: str = None) -> dict():
        """
        Method to unmount array
        """
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "unmount -a {} --force".format(self.array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return True
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))
            return False
        return True

    def reset_devel(self) -> bool:
        """
        Method to array reset
        """
        try:
            cmd = "resetmbr"
            cli_error, jout = self.run_cli_command(cmd, command_type="devel")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to  {}".format(e))

    def delete_array(self, array_name=None) -> bool:
        """
        Method to delete array
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "delete -a {} --force".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def list_volume(self, array_name=None) -> (bool, list, dict()):
        """
        Method to list volumes
        """
        try:
            if array_name != None:
                self.array_name = array_name
            vol_dict = {}
            volumes = []
            cmd = "list -a {}".format(self.array_name)
            cli_error, out = self.run_cli_command(cmd, command_type="volume")

            if cli_error == False:
                raise Exception("CLI Error")
            if out["status_code"] != 0:
                raise Exception(out["description"])
            if len(out["data"]["volumes"]) == 0:
                raise Exception("no volumes present in the array")
            for vol in out["data"]["volumes"]:
                vol_dict[vol["name"]] = {
                    "total": vol["total"],
                    "status": vol["status"],
                    "max_iops": vol["maxiops"],
                    "maxbw": vol["maxbw"],
                }

            return True, list(vol_dict.keys()), vol_dict
        except Exception as e:
            logger.error("list volume command failed with exception {}".format(e))
            return False

    def create_device(
        self, uram_name="uram0", bufer_size="16777216", strip_size="512"
    ) -> bool:
        """
        Method to create malloc device
        """
        try:
            cmd = 'create --device-name {} --num-blocks {} --block-size {} --device-type "uram"'.format(
                uram_name, bufer_size, strip_size
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="device")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def create_volume(self, volumename, size, array_name=None, iops=0, bw=0):
        """
        Method to create volume
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = " create -v {} --size {} --maxiops {} --maxbw {} -a {} ".format(
                volumename, size, iops, bw, array_name
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def delete_volume(self, volumename, array_name) -> bool:
        """
        Method to delete volume
        """
        try:
            cmd = "delete -a {} -v {} ".format(array_name, volumename)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def mount_volume(self, volumename, array_name, nqn=None) -> bool:
        """
        Method to mount volume
        """
        try:
            cmd = "mount -v {} -a {}".format(volumename, array_name)
            if nqn:
                cmd += " --subnqn {}".format(nqn)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def unmount_volume(self, volumename, array_name) -> bool:
        """
        Method to unmount volume
        """
        try:
            cmd = "unmount -v {} -a {}".format(volumename, array_name)
            cli_error, jout = self.run_cli_command(cmd, command_type="volume")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("failed due to {}".format(e))

    def create_subsystem(
        self, nqn_name, ns_count=512, s="POS000000000001", d="POS_VOLUME"
    ) -> bool:
        """
        Method to create nvmf subsystem
        """
        try:
            cmd = "create --subnqn {} --serial-number {} --model-number {} --max-namespaces {} --allow-any-host".format(
                nqn_name, s, d, ns_count
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)

    def list_subsystem(self) -> (bool, list):
        """
        method executes nvmf_get_subsystems
        return bol, output
        """
        try:
            nvmf_out, temp = {}, {}
            out = self.run_cli_command("list", command_type="subsystem")
            for data in out[1]["data"]["subsystemlist"]:
                temp = data
                nvmf_out[data["nqn"]] = temp
            logger.info(nvmf_out)
            return (True, nvmf_out)

        except Exception as e:
            logger.error("Get_nvmf_subsystem failed due to %s" % e)
            return (False, None)

    def add_listner_subsystem(
        self, nqn_name, mellanox_interface, port, transport="TCP"
    ) -> bool:
        """
        Method to add nvmf listner
        """
        try:

            cmd = (
                "add-listener --subnqn {} --trtype {} --traddr {} --trsvcid {}".format(
                    nqn_name, transport, mellanox_interface, port
                )
            )
            cli_error, jout = self.run_cli_command(cmd, command_type="subsystem")
            if cli_error == True:
                if jout["status_code"] == 0:
                    return cli_error
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)

    def create_transport_subsystem(
        self, buf_cache_size=64, num_shared_buf=4096, transport_type="TCP"
    ) -> bool:
        """
        Method to create transport
        """
        try:
            command = "create-transport --trtype {} --buf-cache-size {} --num-shared-buf {} ".format(
                transport_type.upper(), buf_cache_size, num_shared_buf
            )
            out = self.run_cli_command(command, command_type="subsystem")

            if out[0] == True:
                if out[1]["status_code"] == 0:
                    return True
        except Exception as e:
            logger.error(e)

    def info_array(self, array_name: str = None) -> (bool, list, list, str):
        """
        Method to get array information
        """
        spare_dev = []
        data_dev = []
        buffer_dev = []
        try:
            if array_name != None:
                self.array_name = array_name
            cmd = "list -a {}".format(self.array_name)
            out = self.run_cli_command(cmd, command_type="array")
            if out[0] == True:
                if out[1]["output"]["Response"]["result"]["status"]["code"] == 0:
                    flag = True
                else:
                    flag = False
            else:
                logger.error("list array device command execution failed")
                return False, out[1]
            if flag == True:
                array_state = out[1]["data"]["state"]
                array_situation = out[1]["data"]["situation"]
                for dev in out[1]["data"]["devicelist"]:
                    if dev["type"] == "DATA":
                        data_dev.append(dev["name"])
                    elif dev["type"] == "SPARE":
                        spare_dev.append(dev["name"])
                    elif dev["type"] == "BUFFER":
                        buffer_dev.append(dev["name"])
                    else:
                        logger.error("Disk type is unknown")
                        return (False, None)

            else:
                logger.error("failed to execute list_array_device command")
                return False, out[1]
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False, None, None, None
        return (
            True,
            out[1]["data"],
            array_state,
            array_situation,
            data_dev,
            spare_dev,
            buffer_dev,
        )

    def wbt_do_gc(self, array_name: str = None) -> bool:
        """
        Method to do gc
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "do_gc -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    return True
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)

    def wbt_get_gc_status(self, array_name: str = None) -> bool:
        """
        Method to get gc status
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "get_gc_status -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.error(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)

    def wbt_get_gc_threshold(self, array_name: str = None) -> (bool, list):
        """
        Method to get gc threshold
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "get_gc_threshold -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return jout

    def wbt_flush(self, array_name: str = None) -> (bool, list):
        """
        Method to flush
        """
        try:
            if array_name == None:
                array_name = self.array_name
            cmd = "flush -a {}".format(array_name)
            cli_error, jout = self.run_cli_command(cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    logger.info(jout["description"])
                    return True, jout
                else:
                    raise Exception(jout["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)

    def wbt_read_vsamap_entry(
        self, volumename: str, rba: str, array_name: str = None
    ) -> (bool):
        """
        Method to read vsamap entry
        """
        try:
            output_txt_path = "/root/output.txt"

            if Client.is_file_present(output_txt_path) == True:
                delete_cmd = "rm -fr %s" % output_txt_path
                logger.info("Deleting existing output files")
                out = self.ssh_obj.execute(delete_cmd)

            vsamap_entry_cmd = "read_vsamap_entry -v {} --rba {} -a {}".format(
                volumename, rba, array_name
            )
            cli_error, jout = self.run_cli_command(vsamap_entry_cmd, "wbt")
            if cli_error == True:
                if jout["status_code"] == 0:
                    if Client.is_file_present(output_txt_path) == False:
                        raise Exception("output file not generated")
                    else:
                        logger.info("Output.txt file Generated!!!")
                        flag, map_dict = pos.target_utils.wbt_parser(output_txt_path)
                        if flag == True:
                            logger.info(
                                "Successfully data parsed from output.txt file "
                            )
                            return map_dict
                        else:
                            raise Exception("Failed to parse data from output.txt file")
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error(e)
            return jout

    def wbt_read_stripemap_entry(self, vsid: str, array_name: str = None) -> (bool, dict()):
        """
        Method to read stripe map entry
        """
        try:
            logger.info("Executing read_stripemap_entry command")
            output_txt_path = "/root/output.txt"

            if Client.is_file_present(output_txt_path) == True:
                delete_cmd = "rm -fr {}".format(output_txt_path)
                logger.info("Deleting existing output files")
                out = self.ssh_obj.execute(delete_cmd)

            cmd = "read_stripemap_entry --vsid {} -a {}".format(vsid, array_name)
            flag_rs_map, out_rs_map = self.run_cli_command(cmd, "wbt")
            if flag_rs_map == False or int(out_rs_map["data"]["returnCode"]) < 0:
                raise Exception(
                    "Command Execution failed; Please check and Retry again"
                )
            else:
                if Client.is_file_present(output_txt_path) == False:
                    raise Exception("output file not generated")
                else:
                    logger.info("Output.txt file Generated!!!")
                    flag_wbt_par, map_dict_wbt_par = self.wbt_parser(output_txt_path)
                    if flag_wbt_par == True:
                        logger.info("successfully parsed data from output.txt file")
                        return True, map_dict_wbt_par
                    else:
                        raise Exception("failed to parse data from output.txt file")
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            return False, None

    def wbt_translate_device_lba(self, array_name, logical_stripe_id=0, logical_offset=10):
        """
        Method to translate device lba
        """
        try:
            output_txt_path = "/root/output.txt"
            if self.is_file_present(output_txt_path) == True:
                delete_cmd = "rm -fr {}".format(output_txt_path)
                logger.info("Deleting existing output files")

                out = self.ssh_obj.execute(delete_cmd)

            lba_cmd = "translate_device_lba --lsid {} --offset {} -v {}".format(
                logical_stripe_id, logical_offset, array_name
            )

            flag_lba, out_lba = self.run_cli_command(lba_cmd, "wbt")

            if flag_lba == False or int(out_lba["data"]["returnCode"]) < 0:
                raise Exception(
                    "Command Execution failed; Please check and Retry again"
                )
            else:
                if self.is_file_present(output_txt_path) == False:
                    raise Exception("output file not generated")
                else:
                    logger.info("Output.txt file Generated!!!")
                    flag_par_lba, trans_dict_lba = self.wbt_parser(output_txt_path)
                    if flag_par_lba == True:
                        logger.info("Successfully data parsed from output.txt file ")
                        return True, trans_dict_lba
                    else:
                        raise Exception("failed to parse output.txt file")
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            return False, None

    def wbt_write_uncorrectable_lba(self, device_name, lba):
        """
        Method to write uncorrectable lba
        """
        try:
            cmd = "write_uncorrectable_lba --dev {} --lba {}  ".format(device_name, lba)
            out = self.run_cli_command(cmd, command_type="wbt")
            if out[0] == True:
                logger.info("Status_code={}".format(out[1]["status_code"]))
                if (
                    int(out[1]["data"]["returnCode"]) >= 0
                    and out[1]["description"].lower() == "pass"
                    and out[1]["status_code"] == 0
                ):
                    logger.info(
                        "Successfully injected error to the device {} in lba {}".format(
                            device_name, lba
                        )
                    )
                    return True
                else:
                    raise Exception(
                        "Failed to inject error to the device {} in lba {} ".format(
                            device_name, lba
                        )
                    )
        except Exception as e:
            logger.error("command execution failed because  of {}".format(e))
            return False

    def wbt_read_raw(self, dev, lba, count):
        """
        Method to read raw
        """
        try:
            file_name = "/tmp/{}.bin".format(pos.target_utils.random_File_name())
            wbt_cmd = "read_raw --dev {} --lba {} --count {}  --output {} ".format(
                dev, lba, count, file_name
            )
            flag, out = self.run_cli_command(wbt_cmd, "wbt")
            if flag == True and int(out["data"]["returnCode"]) >= 0:
                logger.info(
                    "Successfully executed read_raw command on device  {} from lba {}".format(
                        dev, lba
                    )
                )
                return True, out
            else:
                logger.error(
                    "read_raw command execution failed with return code {} ".format(
                        out["data"]["returnCode"]
                    )
                )
                return False, None
        except Exception as e:
            logger.error("command execution failed because of  {}".format(e))
            return False, None

    def addspare_array(self, device_name: str, array_name: str = None) -> (bool, list):
        """
        Method to add spare drive
        """
        try:
            cmd = "addspare -s {} -a {}".format(device_name, array_name)
            cli_error, out = self.run_cli_command(cmd, command_type="array")
            if cli_error == True:
                status_code = out["status_code"]
                if status_code == 0:
                    logger.info(out["description"])
                    return True, out[1]
                else:
                    raise Exception(out["description"])
            else:
                raise Exception("CLI Error")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False, out[1]


    def core_dump(self):
        """
        Method to collect core dump by giving different options depending on whether poseidonos is running
        :return Bool
        """
        try:
            logger.info(
                "------------------------------------------ CLI HISTORY ------------------------------------------"
            )
            logger.info(self.cli_history)
            for cli_cmd in self.cli_history:
                logger.info(
                    "CMD: {}, STATUS_CODE: {}, ".format(
                        cli_cmd[0], cli_cmd[1]
                    )
                )
            logger.info(
                "-------------------------------------------------------------------------------------------------------"
            )
            command = "ps -aef | grep -i poseidonos"
            out = self.ssh_obj.execute(command)
            command = "pkill -11 poseidonos"
            out = self.ssh_obj.execute(command)
            logger.error("pkill -11 poseidonos for createing core dump file")
            dump_type = "crashed"
            command = "{}/tool/dump/trigger_core_dump.sh {}".format(
                self.pos_path, dump_type
            )
            #out = self.ssh_obj.execute(command)
            #logger.info("core dump file creation: {}".format(out))
            return out
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False
