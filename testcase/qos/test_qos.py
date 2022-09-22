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

import pytest
import logger
import pos
from common_libs import *

logger = logger.get_logger(__name__)


@pytest.mark.sanity
def test_qos_happy_path(array_fixture):
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
    except Exception as e:
        logger.error(e)
        pos.exit_handler()


@pytest.mark.sanity
@pytest.mark.parametrize("num_vol", [1, 256])
def test_qos_set_reset(array_fixture, num_vol):
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = num_vol
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
        assert pos.cli.list_volume(array_name="array1")[0] == True
        for vol in pos.cli.vols:
            assert (
                pos.cli.reset_volume_policy_qos(volumename=vol, arrayname="array1")[0]
                == True
            )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()


@pytest.mark.sanity
def test_qos_rebuilding_Array(array_fixture):
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)

        assert pos.cli.list_array()[0] == True
        for index, array in enumerate(list(pos.cli.array_dict.keys())):
            assert pos.cli.info_array(array_name=array)[0] == True
            assert (
                pos.target_utils.device_hot_remove(
                    device_list=[pos.cli.array_info[array]["data_list"][0]]
                )
                == True
            )
        assert pos.cli.list_volume(array_name="array1")[0] == True
        for vol in pos.cli.vols:
            assert (
                pos.cli.reset_volume_policy_qos(volumename=vol, arrayname="array1")[0]
                == True
            )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()
