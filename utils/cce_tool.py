import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))

from node import SSHclient
import logger
import json

logger = logger.get_logger(__name__)


class POSTarget():

    def __init__(self) -> None:
        self.ssh_obj = None
        self.pos_path = None
        self.pos_version = None
        self.pos_cli = "/bin/poseidonos-cli"
        pass

    def connect(self, ip_addr, user, password, force=False):
        self.ip_addr = ip_addr
        self.user = user
        self.passwrod = password
        ssh_obj = SSHclient(self.ip_addr, self.user, self.passwrod)
        return self.set_connection(ssh_obj, force=force)

    def set_connection(self, ssh_obj, force=False) -> bool:
        if self.ssh_obj:
            logger.warning("Target SSH Connection is Active.")
            if force:
                logger.info("Force update the existing ssh connection..")
                self.ssh_obj = ssh_obj
            else:
               logger.error("Target ssh connection can not be set.")
               return False
        else:
            self.ssh_obj = ssh_obj

        return True

    def get_connection(self):
        return self.ssh_obj

    def set_pos_path(self, path, force=False, verify=False):
        if self.pos_path:
            logger.warning(f"POS path exists. [Old:{self.pos_path}, New: {path}]")
            if not force:
                logger.error("Failed to update POS path")
                return False
        else:
            self.pos_path = path
            logger.info(f"POS path is updated to {self.pos_path}")
            
        # TODO Add verification code
        if verify:
            self.ssh_obj.execute()

        return True

    def get_pos_path(self):
        return self.pos_path
    
    def execute(self, command, pos_cli_cmd=False):
        
        if pos_cli_cmd:
            command = f"{self.get_pos_path()}/{self.pos_cli} {command}"
        
        return self.ssh_obj.execute(command)

    def verify_coverage_enabled(self) -> bool:
        command = "find {} -name *.gcda ".format(self.get_pos_path())
        cmd_out = self.execute(command)

        if len(cmd_out) == 0:
            logger.warning("Coverage is not enabled. Compile POS by enabling gcov.")
            return False

        return True

    def get_gcdacoverage(self):
        pass

    def __del__(self):
        if self.ssh_obj:
            #self.ssh_obj.close()
            pass



class Parser():

    def __init__(self) -> None:
        pass

class CodeCoverage():

    def __init__(self) -> None:
        self.target = POSTarget()
        self.topology_data = None
        pass

    def __config_gcov(self):
        pass

    def load_topology(self, topology_file=None, abs_path=False):
        if not topology_file:
            topology_file = "topology.json"

        if not abs_path:
            file_dir = os.path.join(os.path.dirname(__file__), "../testcase/config_files")
            file_abs_path = os.path.abspath(file_dir)
            file_name = "{}/{}".format(file_abs_path, topology_file)
        else:
            file_name = topology_file
            
        if not os.path.exists(file_name):
            logger.error("File {} does not exist".format(file_name)) 
            return False
        try:
            with open(f"{file_name}") as f:
                self.topology_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read {file_name} due to {e}")
            return False

        return True       

    def connect_target(self, target_obj=None):
        if target_obj:
            if not self.target.set_connection(target_obj, force=True):
                logger.error("Failed to connect to target")
                return False
        else:
            if not self.load_topology() or not self.topology_data:
                logger.warning("Failed to load topology file")

            data_dict = self.topology_data
            tgt_ip_addr = data_dict["login"]["target"]["server"][0]["ip"]
            tgt_user_id = data_dict["login"]["target"]["server"][0]["username"]
            tgt_password = data_dict["login"]["target"]["server"][0]["password"]

            if not self.target.connect(tgt_ip_addr, tgt_user_id, tgt_password):
                logger.error("Failed to connect to target.")
                return False

            tgt_pos_path = data_dict["login"]["paths"]["pos_path"]

        if not self.target.set_pos_path(tgt_pos_path):
            logger.error("Failed to set pos path")

        return True

    def get_code_coverage(self):
        if not self.target.verify_coverage_enabled():
            return
        pass

    def get_parsed_report(self):
        pass

    def get_save_report(self):
        pass


if __name__ == '__main__':
    cc = CodeCoverage()
    cc.connect_target()
    cc.get_code_coverage()