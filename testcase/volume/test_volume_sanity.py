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

from multiprocessing.context import assert_spawning
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


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict, data_store
    pos = POS()
    data_store = {}
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"

    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    assert pos.cli.reset_devel()[0] == True

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
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    assert pos.cli.reset_devel()[0] == True
    assert pos.target_utils.pci_rescan() == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


raid = {
    "RAID0": {"spare": 0, "data": 2},
    "RAID10": {"spare": 2, "data": 2},
    "no-raid": {"spare": 0, "data": 1},
    "RAID5": {"spare": 1, "data": 3},
}


@pytest.mark.sanity
@pytest.mark.parametrize("writeback", [True, False])
@pytest.mark.parametrize("raid_type", list(raid.keys()))
@pytest.mark.parametrize("numvol", [1, 256])
@pytest.mark.parametrize(
    "volsize", ["1mb", None, "1gb"]
)  # None means max size of the array/num of vols per array
def test_SanityVolume(raid_type, writeback, numvol, volsize):
    try:

        logger.info(
            f" ============== Test : RAID {raid_type} writeback {writeback} numvol {numvol}  ============="
        )

        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
            assert pos.cli.reset_devel()[0] == True
            assert pos.target_utils.pci_rescan() == True
        assert pos.cli.list_device()[0] == True
        datalen = raid[raid_type]["data"]
        sparelen = raid[raid_type]["spare"]
        datalist = pos.cli.dev_type["SSD"][0:datalen]
        sparelist = [] if sparelen == 0 else pos.cli.dev_type["SSD"][-sparelen:]
        assert (
            pos.cli.create_array(
                array_name="array1",
                data=datalist,
                write_buffer=pos.cli.dev_type["NVRAM"][0],
                raid_type=raid_type,
                spare=sparelist,
            )[0]
            == True
        )
        array2raid = random.choice(list(raid.keys()))
        datalen = raid[array2raid]["data"]
        sparelen = raid[array2raid]["spare"]
        assert (
            pos.cli.autocreate_array(
                array_name="array2",
                num_data=datalen,
                num_spare=sparelen,
                buffer_name=pos.cli.dev_type["NVRAM"][1],
                raid=array2raid,
            )[0]
            == True
        )

        assert pos.cli.list_device()[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        # assert pos.cli.start_telemetry()[0] == True
        for index, array in enumerate(["array1", "array2"]):
            assert (
                pos.cli.mount_array(array_name=array, write_back=writeback)[0] == True
            )
            expected = True
            if volsize == "1kb":
                expected = False
            if numvol == 257:
                expected = False
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=numvol, size=volsize
                )
                == expected
            )
            assert pos.cli.list_volume(array_name=array)[0] == True
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array,
                    volume_list=pos.cli.vols,
                    nqn_list=[pos.target_utils.ss_temp_list[index]],
                )
                == True
            )

        for array in ["array1", "array2"]:
            assert pos.cli.list_volume(array_name=array)[0] == True
            for vol in pos.cli.vols:
                rlist = [i for i in range(10, 255)]
                newname = random_string(random.choice(rlist))
                assert pos.cli.info_volume(array_name=array, vol_name=vol)[0] == True
                assert (
                    pos.cli.rename_volume(
                        new_volname=newname, volname=vol, array_name=array
                    )[0]
                    == True
                )
                assert (
                    pos.cli.unmount_volume(volumename=newname, array_name=array)[0]
                    == True
                )
                assert (
                    pos.cli.info_volume(array_name=array, vol_name=newname)[0] == True
                )
                assert (
                    pos.cli.delete_volume(volumename=newname, array_name=array)[0]
                    == True
                )

        arrayname = "array1"
        assert pos.cli.info_array(array_name=arrayname)[0] == True
        if raid_type not in ["RAID0", "no-raid"]:
            disklist = [random.choice(pos.cli.dev_type["SSD"])]
            assert pos.target_utils.device_hot_remove(disklist) == True
            # assert pos.cli.unmount_array(array_name=arrayname)[0] == False
            # assert pos.cli.delete_array(array_name=array)[0] == False
            assert pos.target_utils.array_rebuild_wait(array_name=arrayname) == True

        assert pos.cli.info_array(array_name=arrayname)[0] == True

        assert pos.cli.unmount_array(array_name=arrayname)[0] == True
        assert pos.cli.delete_array(array_name=arrayname)[0] == True
        assert pos.cli.list_array()[0] == True
        # assert pos.cli.stop_telemetry()[0] == True

    except Exception as e:
        logger.error(
            f" ======= Test FAILED : RAID {raid_type} writeback {writeback} numvol {numvol}  ========"
        )
        assert 0


@pytest.mark.sanity()
def test_volumesanity257vols():
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
            assert pos.cli.reset_devel()[0] == True
            assert pos.target_utils.pci_rescan() == True
        assert pos.cli.list_device()[0] == True
        assert (
            pos.cli.create_array(
                array_name="array1",
                data=pos.cli.dev_type["SSD"][0:5],
                write_buffer=pos.cli.dev_type["NVRAM"][0],
                raid_type="RAID5",
                spare=[],
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name="array1")[0] == True
        for i in range(256):
            vname = f"array1_vol{str(i)}"
            assert (
                pos.cli.create_volume(
                    volumename=vname, array_name="array1", size="1gb"
                )[0]
                == True
            )
        assert (
            pos.cli.create_volume(
                volumename="invalidvol", array_name="array1", size="1gb"
            )[0]
            == False
        )

    except Exception as e:
        logger.info("test failed")
        assert 0