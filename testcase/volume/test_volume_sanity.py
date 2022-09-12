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

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict, data_store
    pos = POS()
    data_store = {}
    data_dict = pos.data_dict
    data_dict["volume"]["phase"] = "false"
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    
    yield pos


def teardown_function():

    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            for vol in pos.cli.vols:
                assert pos.cli.unmount_volume(volumename = vol, array_name = array)[0] == True
                assert pos.cli.delete_volume(volumename = vol, array_name = array)[0] == True
    
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.sanity
@pytest.mark.parametrize("numvol", [256])
@pytest.mark.parametrize(
    "volsize", ["1mb", "1gb"]
)  # None means max size of the array/num of vols per array
def test_SanityVolume(numvol, volsize):
    try:

        logger.info(
            f" ============== Test : volsize {volsize} numvol {numvol}  ============="
        )

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        for nums in range(numvol):
            volname = f'tempvolpos{str(nums)}'
            assert pos.cli.create_volume(volumename = volname, array_name = "array1", size = volsize)[0] == True
            assert pos.cli.mount_volume(volumename = volname, array_name = "array1")[0] == True
            assert pos.cli.mount_volume(volumename = volname, array_name = "array1")[0] == False
     
    except Exception as e:
        logger.error(
            f" ======= Test FAILED  ========"
        )
        assert 0

   
@pytest.mark.sanity()
def test_volumesanity257vols():
    array_name = "array1"
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
            assert pos.cli.reset_devel()[0] == True
            assert pos.target_utils.pci_rescan() == True
        assert pos.cli.list_device()[0] == True
        
        for i in range(256):
            vname = f"array1_vol{str(i)}"
            assert (
                pos.cli.create_volume(
                    volumename=vname, array_name=array_name, size="1gb"
                )[0]
                == True
            )
            assert pos.cli.mount_volume(volumename = vname, array_name = array_name)[0] == True
        assert (
            pos.cli.create_volume(
                volumename="invalidvol", array_name=array_name, size="1gb"
            )[0]
            == False
        )

    except Exception as e:
        logger.info("test failed")
        assert 0


