#
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

import pytest, json, sys, os, time, signal, psutil, time, random

from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    ALL_COMPLETED,
    FIRST_COMPLETED,
    FIRST_EXCEPTION,
    wait,
)

from pos import POS
import composable.vol_management as volmgmt
import composable.io_management as iomgmt
import composable.system_management as sysmgmt
import composable.composable_core as libcore
from composable.composable_core import _Data as data_mgmt

import logger as logger
logger = logger.get_logger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/../config_files/multi_initiator_ops.json".format(dir_path)) as p:
    tc_dict = json.load(p)


def setup_module():
    global pos
    global data_dict
    pos = POS()
    data_dict = pos.data_dict


def teardown_module():
    pos.exit_handler(expected=True)


def test_vol_lc_stress_io_stress_io_sanity_system_sanity_6_initiator():
    try:
        if pos.client_cnt < 6:
            logger.info(
                "Skipping Test as number of Initiators do not match the TC requirement"
            )
            logger.info(
                "Initiators expected: 6, Actual Initiators: {}".format(pos.client_cnt)
            )
            pytest.skip("Test config not met")

        data_dict["system"]["phase"] = "true"
        data_dict["device"]["phase"] = "true"
        data_dict["array"]["num_array"] = 1
        data_dict["subsystem"]["phase"] = "false"
        data_dict["volume"]["phase"] = "false"

        assert pos.target_utils.pos_bring_up(data_dict) == True
        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        pos.cli.array_name = array_list[0]

        test_dict = tc_dict[
            "test_vol_lc_stress_io_stress_io_sanity_system_sanity_6_initiator"
        ]
        test_object = {
            "vol_management": volmgmt,
            "io_management": iomgmt,
            "system_management": sysmgmt,
        }

        futures = []
        executor = ThreadPoolExecutor()

        total_phase = test_dict["validation"]["totalphase"]
        total_time = test_dict["validation"]["totaltime"]
        por_phase = []
        por_plus_loop = 0
        phase = 0

        if test_dict["validation"]["por"]["ibof"]["npor"]["valid"]:
            por_phase = test_dict["validation"]["por"]["ibof"]["npor"]["phase"].split(
                ","
            )
            por_plus_loop = len(por_phase)

        total_phase = total_phase + por_plus_loop
        time_per_phase = total_time / total_phase

        data_set = []

        for cn in range(test_dict["config"]["initiator"]):
            client_seed = cn
            data_set.append(data_mgmt(client_seed))

        for idx in range(1, total_phase + 1):
            if str(idx) in por_phase:
                start_time = time.time()
                npo_cnt = 1
                while True:
                    assert pos.target_utils.npor_and_save_state() == True
                    for cn in range(test_dict["config"]["initiator"]):
                        assert (
                            libcore.npor_recover(target=pos, data_set=data_set[cn])
                            == True
                        )
                    current_time = time.time()
                    running_time = current_time - start_time
                    if running_time >= time_per_phase:
                        break
                    npo_cnt += 1

            else:

                for cn in range(test_dict["config"]["initiator"]):
                    futures.append(
                        executor.submit(
                            getattr(
                                test_object[
                                    test_dict["validation"]["testcase"][cn]["lib"]
                                ],
                                test_dict["validation"]["testcase"][cn]["name"],
                            ),
                            target=pos,
                            client=pos.client_handle[cn],
                            phase=phase,
                            data_set=data_set[cn],
                            Time=time_per_phase,
                        )
                    )
                    logger.info(
                        "#Test case : {} / {}".format(
                            test_dict["validation"]["testcase"][cn]["lib"],
                            test_dict["validation"]["testcase"][cn]["name"],
                        )
                    )
                done, not_done = wait(futures, return_when=FIRST_EXCEPTION)
                if len(done) != 0:
                    raise_proc = done.pop()
                    if raise_proc.exception() is not None:
                        raise raise_proc.exception()
                phase += 1

        assert pos.target_utils.helper.check_system_memory() == True

        for cn in range(test_dict["config"]["initiator"]):
            if pos.client_handle[cn].ctrlr_list()[1] is not None:
                assert (
                    pos.client_handle[cn].nvme_disconnect(pos.target_utils.ss_temp_list)
                    == True
                )

        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        if len(array_list) == 0:
            logger.info("No array found in the config")
        else:
            for array in array_list:
                assert pos.cli.info_array(array_name=array)[0] == True
                if pos.cli.array_dict[array].lower() == "mounted":
                    assert pos.cli.unmount_array(array_name=array)[0] == True

    except Exception as e:
        pos.exit_handler(expected=False)
        assert 0
