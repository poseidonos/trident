#
#   BSD LICENSE
#   Copyright (c) 2022 Samsung Electronics Corporation
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions
#   are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#        the documentation and/or other materials provided with the
#        distribution.
#      * Neither the name of Samsung Electronics Corporation nor the names of
#        its contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import logger
import json
import os
from traceback import print_exc
from datetime import datetime

logger = logger.get_logger(__name__)


class POS_Config:
    def __init__(self, ssh_obj, file_name="pos.conf", file_path="/etc/pos/") -> None:
        self.ssh_obj = ssh_obj
        self.file_name = file_name
        self.file_path = file_path
        self.file_data = None  # Config File Data in JSON format
        self.file_data_org = None  # Store Files Data original copy
        self.file_modified = False  # Mark ture if config file is update.

    def load_config(self) -> bool:
        try:
            cmd = f"cat {self.file_path}{self.file_name}"
            out = self.ssh_obj.execute(command=cmd, expected_exit_code=0)

            config_data = "".join(out).strip()

            self.file_data = json.loads(config_data)
            self.file_data_org = self.file_data

            logger.debug("Config file data {}.".format(type(self.file_data)))
            return True
        except Exception as e:
            logger.error(f"Load config failed. Error: '{e}'")
            print_exc()
            return False

    def _dump_config_data(self, data: str) -> bool:
        try:
            cmd = f"echo '' > {self.file_path}{self.file_name}"
            self.ssh_obj.execute(command=cmd, expected_exit_code=0)

            for line in data.split("\n"):
                cmd = f"echo '{line}' >> {self.file_path}{self.file_name}"
                self.ssh_obj.execute(command=cmd, expected_exit_code=0)

            return True
        except Exception as e:
            logger.error(f"Load config failed. Error: '{e}'")
            print_exc()
            return False

    def _copy_config_data(self, data: str) -> bool:
        try:
            src_file_name = (
                f'temp_{datetime.now().strftime("%Y_%m_%H_%M")}_pos_conf.json'
            )
            with open(src_file_name, "w") as fp:
                fp.write(f"{data}\n")

            dst_file_name = f"{self.file_path}{self.file_name}"
            self.ssh_obj.file_transfer(
                src_file_name, dst_file_name, move_to_local=False
            )

            os.remove(src_file_name)
            return True
        except Exception as e:
            logger.error(f"Copy config failed. Error: '{e}'")
            print_exc()
            os.remove(src_file_name)
            return False

    def update_config(self, data: dict = None) -> bool:
        try:
            config_data_json = data or self.file_data
            config_data_str = json.dumps(config_data_json, indent=4)

            logger.debug("Config file data {}.".format(config_data_str))

            # return self._dump_config_data(config_data_str)
            return self._copy_config_data(config_data_str)
        except Exception as e:
            logger.error(f"Load config failed. Error: '{e}'")
            print_exc()
            return False

    def restore_config(self, force: bool = False) -> bool:
        try:
            if not self.file_modified:
                logger.error("POS Config file is already in Old state")

            config_data_str = json.dumps(self.file_data_org, indent=4)

            logger.debug("Config file data {}.".format(config_data_str))

            # return self._dump_config_data(config_data_str)
            return self._copy_config_data(config_data_str)
        except Exception as e:
            logger.error(f"Load config failed. Error: '{e}'")
            print_exc()
            return False

    def journal_state(self, enable: bool = True, update_now: bool = False) -> bool:
        journal_enable = self.file_data["journal"]["enable"]
        if enable:
            if journal_enable == "true":
                logger.info("POS Journal is already enabled.")
            else:
                logger.info("Enable POS Journal")
                self.file_data["journal"]["enable"] = "true"
        else:
            if journal_enable == "false":
                logger.info("POS Journal is already disabled.")
            else:
                logger.info("Disable POS Journal")
                self.file_data["journal"]["enable"] = "false"

        if update_now:
            self.file_modified = True
            return self.update_config()

        return True


if __name__ == "__main__":
    pass
    """
    from pos import POS

    pos = POS()
    pos_config = POS_Config(pos.target_ssh_obj)
    assert pos_config.load_config() == True
    assert pos_config.journal_state() == True
    assert pos_config.update_config() == True
    assert pos_config.restore_config() == True
    """
