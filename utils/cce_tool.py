import sys
import os

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../lib")))

from collections import OrderedDict
from datetime import datetime
import json
import logger
from node import SSHclient

logger = logger.get_logger(__name__)


class POSTarget():

    def __init__(self) -> None:
        self.ssh_obj = None
        self.pos_path = None
        self.pos_version = None
        self.pos_cli = "/bin/poseidonos-cli"
        self.lcov_path = None
        self.test_data = OrderedDict()         # test_name: file_name
        self.pre_coverage_varified = False
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

    def _verify_file_esists(self, path, dir_file=False):
        pre_cmd = "if test -{} {} ; then echo 'file_exist'; fi"
        if dir_file:
            command = pre_cmd.format('d', path)
        else:
            command = pre_cmd.format('f', path)

        out = self.ssh_obj.execute(command)
        return "file_exist" in out

    def set_pos_path(self, path, verify=True):
        self.pos_path = path
        logger.info(f"POS path is set to {self.pos_path}")

        if verify:
            return self._verify_file_esists(path, dir_file=True)

        return True

    def get_pos_path(self):
        if not self.pos_path:
            logger.warning(f"POS path is not set.")

        return self.pos_path

    def set_lcov_path(self, path, verify=True):
        self.pos_path = path
        logger.info(f"Lcov path is set to {self.pos_path}")

        if verify:
            return self._verify_file_esists(path)

        return True

    def get_lcov_path(self):
        if not self.lcov_path:
            logger.warning(f"Lcov path is not set.")

        return self.lcov_path

    def execute(self, command, pos_cli_cmd=False):

        if pos_cli_cmd:
            command = f"{self.get_pos_path()}/{self.pos_cli} {command}"

        return self.ssh_obj.execute(command)

    def verify_coverage_pre(self, pos_path=None, lcov_path=None) -> bool:

        pos_path = pos_path or self.get_pos_path()
        if not pos_path:
            logger.error("POS path is not set. Please set POS path.")
            return False

        command = f"find {pos_path} -name *.gcda"
        cmd_out = self.execute(command)
        if len(cmd_out) == 0:
            logger.error(
                "Coverage is not enabled. Compile POS by enabling gcov.")
            return False

        lcov_path = lcov_path or self.get_lcov_path()
        if not lcov_path:
            logger.error("Lcov path is not set. Please set locv path.")
            return False

        self.pre_coverage_varified = True
        return True

    def get_coverage(self, jira_id, unique_key=None):
        if not self.pre_coverage_varified:
            if not self.verify_coverage_pre():
                logger.error("Target code coverage setup ready.")
                return False

        jira_id = jira_id.upper()
        if not unique_key:
            unique_key = datetime.now().strftime('%Y%m%d_%H%M%S')

        cc_out = f"coverage_{jira_id}_{unique_key}.lcov"
        self.test_data[jira_id] = cc_out

        ignore_str = '"/usr/*" "*/ibofos/lib/*"'
        lcov_comds = [f'lcov -c -d src/ --rc lcov_branch_coverage=1 -o {cc_out}',
                      f'lcov --rc lcov_branch_coverage=1 -r {cc_out} {ignore_str} -o {cc_out}']
        try:
            for lcov_cmd in lcov_comds:
                cd_cmd = f"cd {self.get_pos_path()}"
                data_out = self.execute(f"{cd_cmd}; {lcov_cmd}")

            self.over_all_data = "".join(data_out[-3:])
        except Exception as e:
            logger.error("Failed to get the coverage report due to '{e}.")
            return False

        return True

    def generate_html(self):
        pass

    def __del__(self):
        if self.ssh_obj:
            # self.ssh_obj.close()
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
            file_dir = os.path.join(os.path.dirname(
                __file__), "../testcase/config_files")
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

    def get_code_coverage(self, jira_id):
        if not self.target.verify_coverage_pre():
            logger.error("Target code coverage precondition is not done")
            return False

        if not self.target.get_coverage(jira_id=jira_id):
            logger.error("Failed to get code coverage")
            return False

        return True

    def get_parsed_report(self):
        pass

    def get_save_report(self):
        pass


if __name__ == '__main__':
    cc = CodeCoverage()
    assert cc.connect_target()
    assert cc.get_code_coverage("SPS_1100")
