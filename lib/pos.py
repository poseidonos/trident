from node import SSHclient
from cli import Cli
from target_utils import TargetUtils


class POS:
    def __init__(self, ip, username, password, pos_path):
        self.ssh_obj = SSHclient(ip, username, password)
        self.cli = Cli(self.ssh_obj, pos_path)
        self.target_utils = TargetUtils(self.ssh_obj, pos_path)
