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
from pos import POS
import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos
    pos = POS()
    assert pos.target_utils.pos_bring_up() == True
    yield pos
def device():
        logger.info(" ================= DEVICE =================")
        assert pos.cli.list_device()[0] == True
        # assert pos.cli.smart_device(pos.cli.dev_type['SSD'][0])[0] == True
        assert pos.cli.smart_log_device(pos.cli.dev_type["SSD"][0])[0] == True

def qos():
        logger.info(" ================= qos ===================")
        assert pos.cli.list_volume(array_name="array1")[0] == True
        assert (
            pos.cli.create_volume_policy_qos(
                volumename=pos.cli.vols[0],
                arrayname="array1",
                maxiops="1000000000000",
                maxbw="21313123113",
            )[0]
            == True
        )
        assert (
            pos.cli.list_volume_policy_qos(
                volumename=pos.cli.vols[0], arrayname="array1"
            )[0]
            == True
        )
        assert (
            pos.cli.reset_volume_policy_qos(
                volumename=pos.cli.vols[0], arrayname="array1"
            )[0]
            == True
        )
def array():
        logger.info(" ================= ARRAY ===================")
        assert pos.cli.list_array()[0] == True
        volume()
        assert (
            pos.cli.addspare_array(
                device_name=pos.cli.system_disks[0], array_name="array1"
            )[0]
            == True
        )
        assert pos.cli.info_array(array_name="array1")[0] == True
        assert (
            pos.cli.rmspare_array(
                device_name=pos.cli.array_info["array1"]["spare_list"][0],
                array_name="array1",
            )[0]
            == True
        )
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.unmount_array(array_name=array)[0] == True
            assert pos.cli.delete_array(array_name=array)[0] == True

        assert pos.cli.stop_telemetry()[0] == True
        assert pos.cli.reseteventwrr_devel()[0] == True
        
def volume():
        logger.info(" ==================== Volume ===============")
        assert (
            pos.cli.info_volume(array_name="array1", vol_name=pos.cli.vols[0])[0]
            == True
        )
        assert pos.cli.list_volume(array_name="array1")[0] == True
        # assert pos.cli.rename_volume("newvol", pos.cli.vols[0], "array1")[0] == True
        assert pos.cli.unmount_volume(pos.cli.vols[0], "array1")[0] == True
        assert (
            pos.cli.info_volume(array_name="array1", vol_name=pos.cli.vols[0])[0]
            == True
        )
        assert pos.cli.rename_volume("newvol", pos.cli.vols[0], "array1")[0] == True
        assert pos.cli.delete_volume("newvol", "array1")[0] == True
@pytest.mark.sanity
def test_cli_happypath():

    try:
        assert pos.target_utils.get_subsystems_list() == True
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        # assert (
        #    pos.client.fio_generic_runner(
        #        pos.client.nvme_list_out,
        #        fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
        #    )[0]
        #    == True
        # )
        # assert pos.target_utils.get_pos() == True
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True
        device()
        qos()
        
        logger.info("====================GC=====================")
        assert pos.cli.wbt_do_gc()[0] == False
        assert pos.cli.wbt_get_gc_status(array_name="array1")[0] == True

        logger.info(" ================== logger ================")
        assert pos.cli.get_log_level_logger()[0] == True
        assert pos.cli.info_logger()[0] == True
        assert pos.cli.set_log_level_logger(level="debug")[0] == True
        # assert pos.cli.apply_log_filter()[0] == True
        array()
        
        
        logger.info("================== telemetry ===============")
        assert pos.cli.start_telemetry()[0] == True
        logger.info("================== devel ==================")
        assert pos.cli.updateeventwrr_devel("rebuild", "1")[0] == True
        pos.exit_handler(expected = True)        
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()
