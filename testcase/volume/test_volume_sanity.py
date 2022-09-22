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
import random
import logger
from pos import POS

logger = logger.get_logger(__name__)


def random_string(length):
    rstring = ""
    rstr_seq = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(0, length):
        if i % length == 0 and i != 0:
            rstring += "-"
        rstring += str(rstr_seq[random.randint(0, len(rstr_seq) - 1)])
    return rstring


@pytest.mark.sanity
@pytest.mark.parametrize("numvol", [1,256])
@pytest.mark.parametrize(
    "volsize", ["1mb", "1gb"]
)  # None means max size of the array/num of vols per array
def test_SanityVolume(array_fixture, numvol, volsize):
    try:

        logger.info(
            f" ============== Test : volsize {volsize} numvol {numvol}  ============="
        )
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = numvol
        pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = numvol
        pos.data_dict["array"]["num_array"] = 2
        pos.data_dict["volume"]["pos_volumes"][0]["size"] = volsize
        pos.data_dict["volume"]["pos_volumes"][1]["size"] = volsize
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        # negative test Multiple invalid commands
        for nums in range(numvol):
            volname = f"tempvolpos{str(nums)}"
            assert (
                pos.cli.create_volume(
                    volumename=volname, array_name="array33", size=volsize
                )[0]
                == False
            )  # invalid array volume creation
            assert (
                pos.cli.mount_volume(volumename=volname, array_name="array1")[0]
                == False
            )  ##volume re-mount

        assert pos.cli.list_volume(array_name="array1")[0] == True
        for vol in pos.cli.vols:
            rlist = [i for i in range(10, 255)]
            newname = random_string(random.choice(rlist))
            assert pos.cli.info_volume(array_name="array1", vol_name=vol)[0] == True
            assert (
                pos.cli.rename_volume(
                    new_volname=newname, volname=vol, array_name="array1"
                )[0]
                == True
            )
            assert (
                pos.cli.unmount_volume(volumename=newname, array_name="array1")[0]
                == True
            )
            assert pos.cli.info_volume(array_name="array1", vol_name=newname)[0] == True
            assert (
                pos.cli.delete_volume(volumename=newname, array_name="array1")[0]
                == True
            )

    except Exception as e:
        logger.error(f" ======= Test FAILED due to {e} ========")
        assert 0


@pytest.mark.sanity()
def test_volumesanity257vols(array_fixture):
    array_name = "array1"
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["array"]["num_array"] = 1

        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        # negative test
        assert (
            pos.cli.create_volume(
                volumename="invalidvol", array_name=array_name, size="1gb"
            )[0]
            == False
        )

    except Exception as e:
        logger.error(f" ======= Test FAILED due to {e} ========")
        assert 0
