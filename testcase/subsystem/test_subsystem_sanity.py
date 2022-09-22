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
from pos import POS

logger = logger.get_logger(__name__)


@pytest.mark.sanity
def test_sanitySubsystem(array_fixture):
    try:
        pos = array_fixture
        assert pos.target_utils.get_subsystems_list() == True
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        assert pos.target_utils.create_subsystems_multiple(ss_count = 510, base_name = "nqn.2022-10-array1.pos:subsystem") == True       
        assert pos.target_utils.get_subsystems_list() == True

    except Exception as e:
        logger.error(f"TC failed due to {e}")
        assert 0
