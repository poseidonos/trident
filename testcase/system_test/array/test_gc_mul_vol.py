import pytest

import logger
logger = logger.get_logger(__name__)


def test_gc_vol_create_delete(array_fixture):
    logger.info(
        " ==================== Test : test_gc_vol_create_delete ================== "
    )
    try:
        pos = array_fixture
        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert (
            pos.target_utils.create_volume_multiple(
                array_name=array_name, num_vol=4, size="500GB"
            )
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name,
                volume_list=pos.cli.vols,
                nqn=ss_list[0],
            )
            == True
        )
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        assert (
            pos.cli.volume_unmount(array_name=array_name, volumename=pos.cli.vols[-1])[
                0
            ]
            == True
        )
        assert (
            pos.cli.volume_delete(volumename=pos.cli.vols[-1], array_name=array_name)[0]
            == True
        )
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=300"
        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out
        assert pos.client.fio_generic_runner(nvme_devs,
                                             fio_user_data=fio_cmd)[0] == True

        assert pos.client.fio_generic_runner(nvme_devs,
                                             fio_user_data=fio_cmd)[0] == True

        assert pos.cli.wbt_do_gc(array_name = array_name)[0] == True
        assert pos.cli.wbt_get_gc_status(array_name = array_name)[0] == True
        return True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
