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

# from lib.pos import POS
import logger
import random
from common_libs import *

logger = logger.get_logger(__name__)



@pytest.mark.sanity
def test_do_gc_emptyarray(array_fixture):
    try:
        """GC is expected to fail on 100% Free array"""
        pos = array_fixture
        assert pos.cli.wbt_do_gc()[0] == False
    except Exception as e:
        logger.error(e)
        pos.exit_handler()


@pytest.mark.sanity
@pytest.mark.parametrize(
    "raid_type, nr_data_drives",
    [("RAID0", 2), ("RAID10", 4), ("RAID10", 2), ("no-raid", 1), ("RAID10", 8)],)
def test_gcMaxvol(array_fixture, raid_type, nr_data_drives):
    """Trigger garbage collection with longevity of I/O"""
    try:
        pos = array_fixture
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][0]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][1]["write_back"] = random.choice(
            [True, False]
        )
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 0
        pos.data_dict["array"]["pos_array"][1]["spare_device"] = 0
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = 256

        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
        assert pos.cli.wbt_do_gc()[0] == False
        assert pos.cli.wbt_get_gc_status()[0] == True
        

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()
