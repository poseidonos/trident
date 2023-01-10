import pytest

from pos import POS

import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def setup_function():
    data_dict = pos.data_dict
    if pos.target_utils.helper.check_pos_exit() == True:
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

    data_dict["system"]["phase"] = "false"
    data_dict["device"]["phase"] = "false"
    data_dict["subsystem"]["phase"] = "false"
    data_dict["array"]["phase"] = "false"


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.cli.array_list()[0] == True
    for array_name in pos.cli.array_dict.keys():
        assert pos.cli.array_info(array_name=array_name)[0] == True
        if pos.cli.array_dict[array_name].lower() == "mounted":
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol in pos.cli.vols:
                assert (
                    pos.cli.volume_info(array_name=array_name, vol_name=vol)[0] == True
                )

                if pos.cli.volume_data[array_name][vol]["status"] == "Mounted":
                    assert (
                        pos.cli.volume_unmount(volumename=vol, array_name=array_name)[0]
                        == True
                    )
                assert (
                    pos.cli.volume_delete(volumename=vol, array_name=array_name)[0]
                    == True
                )

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.regression
@pytest.mark.parametrize("num_vols", [(5, 10), (20, 40), (128, 64)])
def test_volumes_data_integrity(num_vols):
    """The purpose of test is to create and mount multiple volumes on each array. Run IO and verify data integrity"""
    logger.info("================ Test: test_volumes_data_integrity ================")
    try:
        assert pos.cli.array_list()[0] == True
        for index, array_name in enumerate(pos.cli.array_dict.keys()):
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_data[array_name].get("size"))
            vol_size = f"{int(array_size // (1024 * 1024) / num_vols[index])}mb"  # Volume Size in MB
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name, num_vols[index], size=vol_size
                )
                == True
            )

            assert pos.target_utils.get_subsystems_list() == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
            nqn = ss_list[0]
            assert pos.cli.volume_list(array_name=array_name)
            assert (
                pos.target_utils.mount_volume_multiple(array_name, pos.cli.vols, nqn)
                == True
            )

            assert (
                pos.client.nvme_connect(nqn, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )

        assert pos.client.nvme_list() == True

        # Run IO
        nvme_devs = pos.client.nvme_list_out

        # Block IO
        fio_cmd = (
            "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "
            "--size=2gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        )

        assert (
            pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True
        )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
def test_max_size_volume_data_integrity():
    """The purpose of test is to create and mount max_capacty volume on each array. Run IO and verify data integrity"""
    logger.info(
        "================ Test: test_max_size_volume_data_integrity ================"
    )
    try:
        assert pos.cli.array_list()[0] == True
        for index, array_name in enumerate(pos.cli.array_dict.keys()):
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_data[array_name].get("size"))
            vol_size = f"{int(array_size // (1024 * 1024))}mb"  # Volume Size in MB
            vol_name = "POS_VOL"
            assert (
                pos.cli.volume_create(vol_name, vol_size, array_name=array_name)[0]
                == True
            )

            assert pos.target_utils.get_subsystems_list() == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
            nqn = ss_list[0]
            assert (
                pos.cli.volume_info(array_name=array_name, vol_name=vol_name)[0] == True
            )
            assert pos.cli.volume_mount(vol_name, array_name, nqn)[0] == True

            assert (
                pos.client.nvme_connect(nqn, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )

        assert pos.client.nvme_list() == True

        # Run IO
        nvme_devs = pos.client.nvme_list_out

        # Block IO
        fio_cmd = (
            "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "
            "--size=2gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        )

        assert (
            pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True
        )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)
