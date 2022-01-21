#
#    BSD LICENSE
#    Copyright (c) 2021 Samsung Electronics Corporation
#    All rights reserved.
#
#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions
#    are met:
#
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in
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
import logger, pytest

logger = logger.get_logger(__name__)


def test_create_check(array_management):
    pass


def test_unmount_pos_array(mount_array):
    try:
        assert mount_array.cli.unmount_array()[0] == True
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))
        assert 0


def test_delete_array(array_management):
    try:
        assert array_management.cli.delete_array()[0] == True
    except Exception as e:
        logger.error("testcase failed due to {}".format(e))
        assert 0


def test_create_array_with_out_spare(scan_dev):
    try:
        scan_dev.cli.reset_devel()
        assert scan_dev.cli.create_array(spare=None)[0] == True
        scan_dev.cli.reset_devel()
        scan_dev.cli.create_array()
        scan_dev.cli.mount_array()
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))
        assert 0


def test_array_rebuild(mount_array):
    try:
        array_info = mount_array.cli.info_array()
        data_drives = array_info[4]
        assert (
            mount_array.target_utils.device_hot_remove(device_list=[data_drives[0]])
            == True
        )
        array_info = mount_array.cli.info_array()
        array_state, array_situation = array_info[2], array_info[3]
        if array_state == "BUSY" and array_situation == "REBUILDING":
            logger.info("Array is in rebuilding state")
        else:
            raise Exception("Array is not in rebuilding state")
        mount_array.target_utils.check_rebuild_status()
        assert mount_array.cli.unmount_array()[0] == True
        mount_array.cli.delete_array()
        mount_array.cli.reset_devel()
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))
        assert 0


def test_create_array_2_data_disks(scan_dev):
    try:
        assert scan_dev.cli.create_array(data="unvme-ns-0,unvme-ns-1")[0] == False
        logger.info("as expected array creation failed")
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))
