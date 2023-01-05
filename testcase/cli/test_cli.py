import pytest
from pos import POS
from common_libs import *

import logger
logger = logger.get_logger(__name__)


def device(pos):
    logger.info(" ================= DEVICE =================")
    assert pos.cli.device_list()[0] == True
    # assert pos.cli.device_smart(pos.cli.dev_type['SSD'][0])[0] == True
    assert pos.cli.device_smart_log(pos.cli.dev_type["SSD"][0])[0] == True


def qos(pos):
    logger.info(" ================= qos ===================")
    assert pos.cli.volume_list(array_name="array1")[0] == True
    assert (
        pos.cli.qos_create_volume_policy(
            volumename=pos.cli.vols[0],
            arrayname="array1",
            maxiops="1000000000000",
            maxbw="21313123113",
        )[0]
        == True
    )
    assert (
        pos.cli.qos_list_volume_policy(volumename=pos.cli.vols[0], arrayname="array1")[
            0
        ]
        == True
    )
    assert (
        pos.cli.qos_reset_volume_policy(volumename=pos.cli.vols[0], arrayname="array1")[
            0
        ]
        == True
    )


def array(pos):
    logger.info(" ================= ARRAY ===================")
    assert pos.cli.list_array()[0] == True
    volume(pos)
    assert (
        pos.cli.array_addspare(
            device_name=pos.cli.system_disks[0], array_name="array1"
        )[0]
        == True
    )
    assert pos.cli.array_info(array_name="array1")[0] == True
    assert (
        pos.cli.array_rmspare(
            device_name=pos.cli.array_info["array1"]["spare_list"][0],
            array_name="array1",
        )[0]
        == True
    )
    for array in list(pos.cli.array_dict.keys()):
        assert pos.cli.unmount_array(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True

    assert pos.cli.telemetry_stop()[0] == True
    assert pos.cli.devel_eventwrr_reset()[0] == True


def volume(pos):
    logger.info(" ==================== Volume ===============")
    assert pos.cli.volume_info(array_name="array1", vol_name=pos.cli.vols[0])[0] == True
    assert pos.cli.volume_list(array_name="array1")[0] == True
    # assert pos.cli.volume_rename("newvol", pos.cli.vols[0], "array1")[0] == True
    assert pos.cli.volume_unmount(pos.cli.vols[0], "array1")[0] == True
    assert pos.cli.volume_info(array_name="array1", vol_name=pos.cli.vols[0])[0] == True
    assert pos.cli.volume_rename("newvol", pos.cli.vols[0], "array1")[0] == True
    assert pos.cli.volume_delete("newvol", "array1")[0] == True


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
        assert pos.cli.logger_get_log_level()[0] == True
        assert pos.cli.logger_info()[0] == True
        assert pos.cli.logger_set_log_level(level="debug")[0] == True
        # assert pos.cli.logger_apply_log_filter()[0] == True
        array(pos)

        logger.info("================== telemetry ===============")
        assert pos.cli.telemetry_start()[0] == True
        logger.info("================== devel ==================")
        assert pos.cli.devel_eventwrr_update("rebuild", "1")[0] == True
        # pos.exit_handler(expected = True)
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()
        assert 0
