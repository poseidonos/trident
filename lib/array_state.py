#   BSD LICENSE
#   Copyright (c) 2021 Samsung Electronics Corporation
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
#       the documentation and/or other materials provided with the
#       distribution.
#     * Neither the name of Samsung Electronics Corporation nor the names of
#       its contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#   OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import time
import random
import logger
from pos import POS

logger = logger.get_logger(__name__)


class _Array(POS):
    def __init__(self, array_name="POSARRAY1", data_dict: dict =None, cli_history:list = []):
        super().__init__()

        self.data_dict = data_dict
        self.name = array_name
        self.state = {"current": None, "next": None}
        self.situation = {"current": None, "next": None}
        self.device = {"data": list(), "spare": list(), "rebuild": None}
        self.cli.cli_history = cli_history
        self.func = {
            "name": None,
            "expected": True,
            "param": {"detach_type": None, "pre_write": False},
        }
        self.mbr_device = list()
        self.subsystem = list()
        self.buffer_data = list()
        self.history = [
            [
                "index",
                "command",
                "array",
                "current state",
                "next state",
                "data",
                "spare",
                "detach type",
                "expected",
            ]
        ]

    def current_system_state(self):
        assert self.cli.list_array()[0] == True
        array_list = list(self.cli.array_dict.keys())
        if len(array_list) == 0:
            logger.info("----- CURRENT ARRAY STATE : NO ARRAY PRESENT IN THE CONFIG ----")
        else:
            logger.info(f' -------------- ARRAY MOUNT/UNMOUNT INFO {self.cli.array_dict} --------------')
            array_dict = {}
            for array in array_list:
                if self.name == array:
                    assert self.cli.info_array(array_name=self.name)[0] == True
                    state = self.cli.array_info[self.name]["state"].lower()
                    situation = self.cli.array_info[self.name]["situation"].lower()
                    array_dict[self.name] = {
                        "state": state,
                        "situatation": situation,
                        "data": self.cli.array_info[self.name]["data_list"],
                        "spare": self.cli.array_info[self.name]["spare_list"],
                    }
                    logger.info(f"--------- CURRENT ARRAY STATE : {array_dict} -------------------")
        return True

    def select_next_state(self):
        """
        Method to determine the next array state based on current array state and the number of disks
        """
        list_func = [
            "mount_system",
            "unmount_array",
            "delete_array",
            "create_array",
            "wait_for_rebuild",
            "add_spare",
            "hot_swap",
        ]

        def init_obj():
            assert self.cli.list_device()[0] == True
            out = check_array_in_list(array=self.name)
            if out is True:
                assert self.cli.info_array(array_name=self.name)[0] == True
                self.state["current"] = self.cli.array_info[self.name]["state"].lower()
                self.situation["current"] = self.cli.array_info[self.name][
                    "situation"
                ].lower()

                self.device["data"] = self.cli.array_info[self.name]["data_list"]
                self.device["spare"] = self.cli.array_info[self.name]["spare_list"]
                if "Faulty Device" in self.device["data"]:

                    self.device["data"] = list(
                        set(self.device["data"]) - set(["Faulty Device"])
                    )

            else:
                assert update_next_status(state=None, situation=None) == True
                self.device["data"].clear()
                self.device["spare"].clear()
                self.state["current"] = None
                self.situation["current"] = None
            self.func["name"] = random.choice(list_func)
            self.func["expected"] = True
            self.func["param"]["detach_type"] = None
            return True

        def update_next_status(state=None, situation=None, expected=True):
            self.state["next"] = state
            self.situation["next"] = situation
            self.func["expected"] = expected
            return True

        def check_array_in_list(array):
            assert self.cli.list_array()[0] == True

            array_list = list(self.cli.array_dict.keys())

            if len(array_list) == 0:
                logger.info("there is no array in the config")
                return False
            else:
                for array in array_list:

                    if self.name == array:
                        logger.info("the array existed in array list")
                        return True
                return False

        assert init_obj() == True
        assert self.cli.list_device()[0] == True
        self.total_data_array = len(self.cli.array_info[self.name]["data_list"])

        if self.name == "Trident_POS_Array1":
            self.totalDrivesArray = int(
                self.data_dict["array"]["array1_data_count"]
            ) + int(
                self.data_dict["array"]["array1_spare_count"]
            )  ##Num Spare + Num Data
        else:
            self.totalDrivesArray = int(
                self.data_dict["array"]["array2_data_count"]
            ) + int(self.data_dict["array"]["array2_spare_count"])

        if "wait_for_rebuild" == self.func["name"]:
            if "rebuilding" == self.situation["current"]:
                assert (
                    update_next_status(
                        state="normal", situation="normal", expected=True
                    )
                    == True
                )
            else:
                assert (
                    update_next_status(
                        state=self.state["current"],
                        situation=self.situation["current"],
                        expected=True,
                    )
                    == True
                )

        elif "hot_swap" == self.func["name"]:
            self.func["param"]["detach_type"] = random.choice(
                ["data", "spare"] if len(self.device["spare"]) > 0 else ["data"]
            )
            if self.func["param"]["detach_type"] == "spare":
                assert (
                    update_next_status(
                        state=self.state["current"],
                        situation=self.situation["current"],
                        expected=True,
                    )
                    == True
                )
            else:
                if "default" == self.situation["current"]:
                    if len(self.device["data"]) == self.total_data_array:
                        assert (
                            update_next_status(
                                state=self.state["current"],
                                situation=self.situation["current"],
                                expected=True,
                            )
                            == True
                        )
                    elif len(self.device["data"]) < self.total_data_array:
                        assert (
                            update_next_status(
                                state="stop", situation="fault", expected=True
                            )
                            == True
                        )
                elif "normal" == self.situation["current"]:
                    if len(self.device["spare"]) > 0:
                        assert (
                            update_next_status(
                                state="busy", situation="rebuilding", expected=True
                            )
                            == True
                        )
                        self.device["rebuild"] = "".join(self.device["spare"][-1])
                    else:
                        assert (
                            update_next_status(
                                state="busy", situation="degraded", expected=True
                            )
                            == True
                        )
                elif "degraded" == self.situation["current"]:
                    assert (
                        update_next_status(
                            state="stop", situation="fault", expected=True
                        )
                        == True
                    )
                elif "rebuilding" == self.situation["current"]:
                    if self.device["rebuild"] != None:
                        self.func["param"]["detach_type"] = random.choice(
                            [self.func["param"]["detach_type"], "rebuild"]
                        )
                    if self.func["param"]["detach_type"] == "rebuild":
                        if len(self.device["spare"]) > 0:
                            assert (
                                update_next_status(
                                    state="busy", situation="rebuilding", expected=True
                                )
                                == True
                            )
                        else:
                            assert (
                                update_next_status(
                                    state="busy", situation="degraded", expected=True
                                )
                                == True
                            )
                    elif self.func["param"]["detach_type"] == "data":
                        assert (
                            update_next_status(
                                state="stop", situation="fault", expected=True
                            )
                            == True
                        )
                    else:
                        logger.info(
                            "wrong detach type was selected (detach type={}".format(
                                self.func["param"]["detach_type"]
                            )
                        )
                else:
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=True,
                        )
                        == True
                    )

        elif "add_spare" == self.func["name"]:
            if len(self.cli.system_disks) == 0:
                logger.info("there is no system device to add as spare device")
                assert (
                    update_next_status(
                        state=self.state["current"],
                        situation=self.situation["current"],
                        expected=True,
                    )
                    == True
                )
            else:
                if (
                    "normal" == self.situation["current"]
                    and self.data_dict["array"]["num_array"] > 1
                ):
                    logger.info("Skip the add spare because array has full data device")
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=True,
                        )
                        == True
                    )
                elif (
                    "rebuilding" == self.situation["current"]
                    and self.data_dict["array"]["num_array"] > 1
                ):
                    logger.info("Skip the add spare because array has full data device")
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=True,
                        )
                        == True
                    )
                elif "default" == self.situation["current"]:
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=False,
                        )
                        == True
                    )
                elif "degraded" == self.situation["current"]:
                    assert (
                        update_next_status(
                            state="busy", situation="rebuilding", expected=True
                        )
                        == True
                    )
                elif "fault" == self.situation["current"]:
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=False,
                        )
                        == True
                    )
                elif None == self.situation["current"]:
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=False,
                        )
                        == True
                    )
                else:
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=True,
                        )
                        == True
                    )

        elif "create_array" == self.func["name"]:
            if None == self.situation["current"]:
                if len(self.cli.system_disks) < self.total_data_array:
                    assert (
                        update_next_status(
                            state=self.state["current"],
                            situation=self.situation["current"],
                            expected=False,
                        )
                        == True
                    )
                else:
                    assert (
                        update_next_status(
                            state="offline", situation="default", expected=True
                        )
                        == True
                    )
            else:
                assert (
                    update_next_status(
                        state=self.state["current"],
                        situation=self.situation["current"],
                        expected=False,
                    )
                    == True
                )

        elif "delete_array" == self.func["name"]:
            if "default" == self.situation["current"]:
                self.func["param"]["pre_write"] = False
                assert (
                    update_next_status(state=None, situation=None, expected=True)
                    == True
                )
            elif "fault" == self.situation["current"]:
                self.func["param"]["pre_write"] = False
                assert (
                    update_next_status(state=None, situation=None, expected=True)
                    == True
                )
            else:
                assert (
                    update_next_status(
                        state=self.state["current"],
                        situation=self.situation["current"],
                        expected=False,
                    )
                    == True
                )

        elif "mount_system" == self.func["name"]:
            if "default" == self.situation["current"]:

                if len(self.device["data"]) == self.total_data_array:
                    assert (
                        update_next_status(
                            state="normal", situation="normal", expected=True
                        )
                        == True
                    )
                elif len(self.device["data"]) < self.total_data_array:
                    if len(self.device["spare"]) == 0:
                        assert (
                            update_next_status(
                                state="busy", situation="degraded", expected=True
                            )
                            == True
                        )
                    else:
                        assert (
                            update_next_status(
                                state="busy", situation="rebuilding", expected=True
                            )
                            == True
                        )
                        self.device["rebuild"] = "".join(self.device["spare"][-1])
            else:
                assert (
                    update_next_status(
                        state=self.state["current"],
                        situation=self.situation["current"],
                        expected=False,
                    )
                    == True
                )

        elif "unmount_array" == self.func["name"]:
            if self.situation["current"] in ["normal", "degraded"]:
                assert (
                    update_next_status(
                        state="offline", situation="default", expected=True
                    )
                    == True
                )
            else:
                assert (
                    update_next_status(
                        state=self.state["current"],
                        situation=self.situation["current"],
                        expected=False,
                    )
                    == True
                )

        else:
            logger.info("next function is wrong value : {}".format(self.func["name"]))
            return False
        self.current_system_state()
        logger.info(
            "--- ARRAY NAME : {}---- NEXT STATE: {}/{} -- FUNCTION: {} -- DETACH: {} ----------".format(
                self.name,
                self.state["next"],
                self.situation["next"],
                self.func["name"],
                self.func["param"]["detach_type"],
            )
        )
        return True

    def check_next_state(self):
        """
        Method to verify next array state after executing a specific function

        """

        self.current_system_state()
        assert self.cli.list_array()[0] == True
        array_list = list(self.cli.array_dict.keys())
        if self.func["name"] == "delete_array" and self.func["expected"] == True:
            if len(array_list) == 0:
                logger.info(
                    "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                        self.name,
                        self.func["name"],
                        self.state["next"],
                        self.situation["next"],
                        None,
                        None,
                    )
                )
                return True
            else:
                for array in array_list:
                    if self.name == array:
                        assert self.cli.info_array(array_name=self.name)[0] == True
                        state = self.cli.array_info[self.name]["state"].lower()
                        situation = self.cli.array_info[self.name]["situation"].lower()
                        logger.info(
                            "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : FAIL (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                                self.name,
                                self.func["name"],
                                self.state["next"],
                                self.situation["next"],
                                state,
                                situation,
                            )
                        )
                        return False
                logger.info(
                    "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                        self.name,
                        self.func["name"],
                        self.state["next"],
                        self.situation["next"],
                        None,
                        None,
                    )
                )
                return True
        else:
            if len(array_list) == 0:
                state = None
                situation = None
            else:
                for array in array_list:
                    if self.name == array:
                        assert self.cli.info_array(array_name=self.name)[0] == True
                        state = self.cli.array_info[self.name]["state"].lower()
                        situation = self.cli.array_info[self.name]["situation"].lower()
                        break
                    else:
                        state = None
                        situation = None

            if state == self.state["next"] and situation == self.situation["next"]:
                logger.info(
                    "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                        self.name,
                        self.func["name"],
                        self.state["next"],
                        self.situation["next"],
                        state,
                        situation,
                    )
                )
                return True
            else:
                if self.situation["current"] == "rebuilding":
                    if situation in ["normal", "rebuilding"]:
                        logger.info(
                            "Rebuilding was completed before the function was executed."
                        )
                        self.state["next"] = state
                        self.situation["next"] = situation
                        logger.info(
                            "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                                self.name,
                                self.func["name"],
                                self.state["next"],
                                self.situation["next"],
                                state,
                                situation,
                            )
                        )
                        return True
                    elif situation == "degraded" and self.func["name"] == "hot_swap":
                        logger.info(
                            "Rebuilding was completed before the function was executed."
                        )
                        self.state["next"] = state
                        self.situation["next"] = situation
                        logger.info(
                            "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                                self.name,
                                self.func["name"],
                                self.state["next"],
                                self.situation["next"],
                                state,
                                situation,
                            )
                        )
                        return True
                elif self.situation["current"] == "normal":
                    if situation in ["normal", "rebuilding"]:
                        logger.info("Rebuilding started after mountarray")
                        self.state["next"] = state
                        self.situation["next"] = situation
                        logger.info(
                            "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                                self.name,
                                self.func["name"],
                                self.state["next"],
                                self.situation["next"],
                                state,
                                situation,
                            )
                        )
                        return True
                elif self.situation["next"] == "rebuilding":
                    if situation in ["normal", "degraded"]:
                        logger.info(
                            "Rebuilding was completed before the function was executed."
                        )
                        self.state["next"] = state
                        self.situation["next"] = situation
                        logger.info(
                            "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                                self.name,
                                self.func["name"],
                                self.state["next"],
                                self.situation["next"],
                                state,
                                situation,
                            )
                        )
                        return True
                elif (
                    self.situation["next"] == "default"
                    and self.func["name"] == "hot_swap"
                ):
                    if situation in ["fault", "offline", "stop"]:
                        logger.info("more than one faulty device present in the array.")
                        self.state["next"] = state
                        self.situation["next"] = situation
                        logger.info(
                            "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : PASS (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                                self.name,
                                self.func["name"],
                                self.state["next"],
                                self.situation["next"],
                                state,
                                situation,
                            )
                        )
                        return True

                logger.info(
                    "--- ARRAY NAME : {}--- OPERATION : {} ---- CHECK ARRAY STATE : FAIL (EXPECTED : {}/{}, ACTUAL : {}/{}) -------".format(
                        self.name,
                        self.func["name"],
                        self.state["next"],
                        self.situation["next"],
                        state,
                        situation,
                    )
                )
                return False
        a

    def run_func(self, list_array_obj=None):
        """
        Method to run specific functions
        """

        def get_buffer_data():
            assert self.cli.list_device()[0] == True
            assert self.cli.list_array()[0] == True
            array_list = list(self.cli.array_dict.keys())
            if len(array_list) == 0:
                logger.info("No array Exist all buffer can be overridden")
                self.buffer_data = self.cli.dev_type["NVRAM"]
            elif len(array_list) == len(self.cli.dev_type["NVRAM"]):
                logger.warning("No free NVRAM")
                self.buffer_data = self.cli.dev_type["NVRAM"]
            else:
                used_bufer = []
                for array in array_list:
                    assert self.cli.info_array(array_name=array)[0] == True
                    used_bufer.append(self.cli.array_info[array]["buffer_list"][0])
               
                free_buf = [
                    buf for buf in self.cli.dev_type["NVRAM"] if buf not in used_bufer
                ]
                self.buffer_data = free_buf
          
            return True

        def check_mbr_device(device=None):
            """
            Method to check if device can be included in this array
            device: str (ex. unvme-ns-0)
            """
            assert self.cli.list_device()[0] == True
            target_bdf = self.cli.NVMe_BDF[device]["addr"]
            logger.info("check mbr device: {}({})".format(device, target_bdf))
            for array_obj in list_array_obj:
                if array_obj.name == self.name:
                    continue
                if target_bdf in array_obj.mbr_device:
                    logger.info(
                        "{} device has mbr from other array: {}({})".format(
                            device, array_obj.name, array_obj.mbr_device
                        )
                    )
                    return False
            return True

        def select_system_device(dev_num=None):
            device_list = list()
            assert self.cli.list_device()[0] == True
            sys_devices = self.cli.system_disks
            for num in range(dev_num):
                device = random.choice(sys_devices)
                device_list.append(device)
                sys_devices.remove(device)
            assert self.cli.list_device()[0] == True
            return device_list

        def func0_wait_for_rebuild():
            logger.info(
                "[Func0] wait for rebuild complete (Expected result : {})".format(
                    self.func["expected"]
                )
            )
            array_status = self.situation["next"]
            if array_status is None:
                return True
            else:
                count = 0
                while True:
                    time.sleep(2)
                    out = self.cli.info_array(array_name=self.name)[0]
                    if out is False:
                        return False
                    if (
                        self.cli.array_info[self.name]["situation"].lower()
                        == array_status
                    ):
                        return True
                    count = count + 1
                    if count > 30 * 60 * 3:
                        return False

        def func1_hot_swap():
            logger.info(
                "[Func1] hot swap device (Expected result : {})".format(
                    self.func["expected"]
                )
            )

            dev_name = None

            assert self.cli.list_device()[0] == True
            assert self.cli.list_array()[0] == True
            array_list = list(self.cli.array_dict.keys())

            if len(array_list) == 0:
                assert self.cli.list_device()[0] == True

                bdf = self.cli.NVMe_BDF[random.choice(self.cli.system_disks)]["addr"]
                dev_name = "".join(
                    [
                        name
                        for name, value in self.cli.NVMe_BDF.items()
                        if value["addr"] == bdf
                    ]
                )
            else:
                detach_type = self.func["param"]["detach_type"]
                if len(self.device[detach_type]) == 0:
                    logger.info("There is no device to detach")
                    return True
                else:
                    if detach_type == "data":
                        if self.situation["current"] == "rebuilding":
                            self.device["data"].remove(self.device["rebuild"])
                        if "Faulty Device" in self.device["data"]:

                            temp_list = list(
                                set(self.device["data"]) - set(["Faulty Device"])
                            )
                            if len(temp_list) == 0:
                                logger.info("no devices Present in Array to remove")
                                return True
                            else:
                                dev_name = random.choice(temp_list)
                        else:
                            dev_name = random.choice(self.device["data"])

                    elif detach_type == "spare":
                        dev_name = random.choice(self.device["spare"])
                    elif detach_type == "rebuild":
                        dev_name = self.device["rebuild"]
                        if len(self.device["spare"]) > 0:
                            self.device["rebuild"] = "".join(self.device["spare"][-1])
                        else:
                            self.device["rebuild"] = None
                    else:
                        dev_name = random.choice(
                            self.device["data"] + self.device["spare"]
                        )
                    bdf = self.cli.NVMe_BDF[dev_name]["addr"]

                    if self.state["current"] in ["offline", "stop"]:
                        self.mbr_device.append(bdf)
            assert (
                self.target_utils.device_hot_remove([dev_name]) == self.func["expected"]
            )
            assert self.target_utils.pci_rescan() == self.func["expected"]

            return True

        def func2_add_spare_dev():
            logger.info(
                "[Func2] add device as spare device (Expected result : {})".format(
                    self.func["expected"]
                )
            )
            assert self.cli.list_device()[0] == True
            if len(self.cli.system_disks) == 0:
                logger.info("There is no system device to add as spare device")
                return True
            else:
                if (
                    "normal" == self.situation["current"]
                    and self.data_dict["array"]["num_array"] > 1
                ):
                    logger.info("Skip the add spare because array has full data device")
                    return True
                elif (
                    "rebuilding" == self.situation["current"]
                    and self.data_dict["array"]["num_array"] > 1
                ):
                    logger.info("Skip the add spare because array has full data device")
                    return True
                target_dev = random.choice(self.cli.system_disks)
                out = check_mbr_device(device=target_dev)
                if out is True:
                    if (
                        self.situation["current"] == "degraded"
                        and self.func["expected"] == True
                    ):
                        self.device["rebuild"] = target_dev
                else:
                    logger.info("Expected result is changed to False due to mbr device")
                    self.state["next"] = self.state["current"]
                    self.situation["next"] = self.situation["current"]
                    self.func["expected"] = False
                assert (
                    self.cli.addspare_array(
                        device_name=target_dev, array_name=self.name
                    )[0]
                    == self.func["expected"]
                )

                if self.func["expected"] == True:
                    assert self.cli.info_array(array_name=self.name)[0] == True
                    if target_dev in self.cli.array_info[self.name]["spare_list"]:
                        logger.info("Successfully check if device is added")
                        return True
                    else:
                        if target_dev in self.cli.array_info[self.name]["data_list"]:
                            assert self.cli.info_array(array_name=self.name)[0] == True
                            if (
                                self.cli.array_info[self.name]["situation"].lower()
                                == "rebuilding"
                            ):
                                logger.info("Successfully check if device is added")
                                return True
                    return False
            return True

        def func3_create_array():
            logger.info(
                "[Func3] create array with {} devices with Expected result : {})".format(
                    str(self.total_data_array), self.func["expected"]
                )
            )
            assert self.cli.list_device()[0] == True

            if len(self.cli.system_disks) < self.totalDrivesArray:
                buffer_dev = ["uram{}".format(self.name[-1:])][0]
                data_dev = ["unvme-ns-0", "unvme-ns-1", "unvme-ns-2", "unvme-ns-3"]
                spare_dev = []

                assert (
                    self.cli.create_array(
                        write_buffer=buffer_dev,
                        data=data_dev,
                        spare=spare_dev,
                        array_name=self.name,
                        raid_type="RAID5",
                    )[0]
                    == self.func["expected"]
                )
            else:
                index = int(self.name[-1:])

                sysdev_list = select_system_device(dev_num=self.totalDrivesArray)
                data_dev = sysdev_list[0 : self.data_dict["array"]["array1_data_count"]]
                spare_dev = sysdev_list[
                    self.data_dict["array"]["array1_data_count"] : self.data_dict[
                        "array"
                    ]["array1_data_count"]
                    + self.data_dict["array"]["array1_spare_count"]
                ]
                device_list = data_dev + spare_dev
                get_buffer_data()
                buffer_dev = self.buffer_data
                for target_dev in device_list:
                    out = check_mbr_device(device=target_dev)

                    if out is False:
                        logger.info(
                            "Expected result is changed to False due to mbr device"
                        )
                        self.state["next"] = self.state["current"]
                        self.situation["next"] = self.situation["current"]
                        self.func["expected"] = False

                assert (
                    self.cli.create_array(
                        write_buffer=buffer_dev[0],
                        data=data_dev,
                        spare=spare_dev,
                        array_name=self.name,
                        raid_type="RAID5",
                    )[0]
                    == self.func["expected"]
                )
            return True

        def func4_delete_array():
            logger.info(
                "[Func4] delete array (Expected result : {})".format(
                    self.func["expected"]
                )
            )
            assert (
                self.cli.delete_array(array_name=self.name)[0] == self.func["expected"]
            )
            assert self.target_utils.get_subsystems_list() == True
            if self.func["expected"] == True:
                self.subsystem = self.target_utils.ss_temp_list
                if len(self.subsystem) > 1:
                    for subsystem in self.subsystem:
                        if self.name in subsystem:
                            self.client.nvme_list()
                            if len(self.client.nvme_list_out) != 0:
                                self.client.nvme_disconnect(nqn = [subsystem])
                        assert (
                            self.cli.delete_subsystem(nqn_name=subsystem)[0]
                            == self.func["expected"]
                        )
                self.subsystem = list()
                self.mbr_device = list()
                self.device["rebuild"] = None
            return True

        def func5_mount_system():
            logger.info(
                "[Func5] mount array and set config for normal state (Expected result : {})".format(
                    self.func["expected"]
                )
            )
            assert (
                self.cli.mount_array(array_name=self.name)[0] == self.func["expected"]
            )
            self.target_utils.helper.get_mellanox_interface_ip()
            assert self.target_utils.get_subsystems_list() == True
            if self.func["expected"] == True:
                assert self.cli.list_volume(array_name=self.name)[0] == True
                base_name =  base_name = self.data_dict["subsystem"]["base_nqn_name"] + self.name
                self.target_utils.create_subsystems_multiple(
                    ss_count=self.data_dict["subsystem"][self.name], base_name = base_name
                ) == True
                self.target_utils.get_subsystems_list()
                self.subsystem = [ss for ss in self.target_utils.ss_temp_list if self.name in ss]
                for ss in self.subsystem:
                    self.cli.add_listner_subsystem(
                        ss, self.target_utils.helper.ip_addr[0], "1158"
                    )
                if len(self.cli.vols) != 0:

                    for index, volname in enumerate(self.cli.vols):
                        assert (
                            self.cli.mount_volume(
                                volumename=volname,
                                nqn=self.subsystem[index],
                                array_name=self.name,
                            )[0]
                            == True
                        )

                else:
                    assert (
                        self.target_utils.create_volume_multiple(
                            array_name=self.name,
                            num_vol=self.data_dict["volume"][self.name]["num_vol"],
                            size=self.data_dict["volume"][self.name]["size"],
                        )
                        == True
                    )
                    assert self.cli.list_volume(self.name)[0] == True
                    assert self.target_utils.mount_volume_multiple(
                        array_name=self.name,
                        volume_list=self.cli.vols,
                        nqn_list=self.subsystem,
                    )

                self.target_utils.get_subsystems_list()
                self.subsystem = self.target_utils.ss_temp_list
                for nqn_name in self.subsystem:
                    assert (
                        self.client.nvme_connect(
                            nqn_name, self.target_utils.helper.ip_addr[0], "1158"
                        )
                        == True
                    )
                assert self.client.nvme_list() == True
                self.mbr_device = list()
                if self.func["param"]["pre_write"] == False:
                    assert self.client.nvme_list() == True

                    assert (
                        self.client.fio_generic_runner(
                            self.client.nvme_list_out,
                            fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --size=100%",
                        )[0]
                        == True
                    )
                    self.func["param"]["pre_write"] = True
            return True

        def func6_unmount_array():
            logger.info(
                "[Func6] unmount array (Expected result : {})".format(
                    self.func["expected"]
                )
            )
            if self.func["expected"] == True:
                self.client.nvme_disconnect(self.subsystem) == True
            out = self.cli.unmount_array(array_name=self.name)[0]
            if out != self.func["expected"]:
                if self.situation["current"] == "rebuilding":
                    assert self.cli.info_array(array_name=self.name)[0] == True
                    cur_state = self.cli.array_info[self.name]["state"].lower()
                    cur_situation = self.cli.array_info[self.name]["situation"].lower()
                    if cur_situation == "default":
                        self.func["expected"] = True
                        self.state["next"] = cur_state
                        self.situation["next"] = cur_situation
                        self.client.nvme_disconnect(self.subsystem) == True
                        return True
                return False
            else:
                return True

        dict_func = {
            "wait_for_rebuild": func0_wait_for_rebuild,
            "hot_swap": func1_hot_swap,
            "add_spare": func2_add_spare_dev,
            "create_array": func3_create_array,
            "delete_array": func4_delete_array,
            "mount_system": func5_mount_system,
            "unmount_array": func6_unmount_array,
        }
        assert dict_func[self.func["name"]]() == True
        return True

    def cmd_history(self, exit=False, loop=None):
        cmd = [
            loop,
            self.func["name"],
            self.name,
            self.situation["current"],
            self.situation["next"],
            len(self.device["data"]),
            len(self.device["spare"]),
            self.func["param"]["detach_type"],
            self.func["expected"],
        ]
        if len(self.history) > 100000:
            del self.history[1]
        self.history.append(cmd)
        if exit is True:
            logger.info(
                "------------------------------------ CMD HISTORY : {} ------------------------------------".format(
                    self.name
                )
            )
            for command in self.history:
                logger.info(command)
            logger.info(
                "------------------------------------------------------------------------------------------"
            )
        return True
