import pytest
from pos import POS
from common_libs import *

import logger
logger = logger.get_logger(__name__)


def device(pos):
    logger.info(" ================= DEVICE =================")
    assert pos.cli.list_device()[0] == True
    # assert pos.cli.smart_device(pos.cli.dev_type['SSD'][0])[0] == True
    assert pos.cli.smart_log_device(pos.cli.dev_type["SSD"][0])[0] == True


def qos(pos):
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
        pos.cli.list_volume_policy_qos(volumename=pos.cli.vols[0], arrayname="array1")[
            0
        ]
        == True
    )
    assert (
        pos.cli.reset_volume_policy_qos(volumename=pos.cli.vols[0], arrayname="array1")[
            0
        ]
        == True
    )


def array(pos):
    logger.info(" ================= ARRAY ===================")
    assert pos.cli.list_array()[0] == True
    volume(pos)
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


def volume(pos):
    logger.info(" ==================== Volume ===============")
    assert pos.cli.info_volume(array_name="array1", vol_name=pos.cli.vols[0])[0] == True
    assert pos.cli.list_volume(array_name="array1")[0] == True
    # assert pos.cli.rename_volume("newvol", pos.cli.vols[0], "array1")[0] == True
    assert pos.cli.unmount_volume(pos.cli.vols[0], "array1")[0] == True
    assert pos.cli.info_volume(array_name="array1", vol_name=pos.cli.vols[0])[0] == True
    assert pos.cli.rename_volume("newvol", pos.cli.vols[0], "array1")[0] == True
    assert pos.cli.delete_volume("newvol", "array1")[0] == True


@pytest.mark.sanity
def test_cli_happypath(array_fixture):

    try:
        pos = array_fixture
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True
        device(pos)
        qos(pos)

        logger.info("====================GC=====================")
        pos.cli.wbt_do_gc()
        pos.cli.wbt_get_gc_status(array_name="array1")

        logger.info(" ================== logger ================")
        assert pos.cli.get_log_level_logger()[0] == True
        assert pos.cli.info_logger()[0] == True
        assert pos.cli.set_log_level_logger(level="debug")[0] == True
        # assert pos.cli.apply_log_filter()[0] == True
        array(pos)

        logger.info("================== telemetry ===============")
        assert pos.cli.start_telemetry()[0] == True
        logger.info("================== devel ==================")
        assert pos.cli.updateeventwrr_devel("rebuild", "1")[0] == True
        # pos.exit_handler(expected = True)
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()
        assert 0
