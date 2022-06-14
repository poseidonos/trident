import pytest
import logger
import pos

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = pos.POS()
    data_store = {}
    data_dict = pos.data_dict
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.helper.check_system_memory() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    pos.target_utils.get_subsystems_list()
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
            assert pos.cli.list_volume(array)[0] == True
            for vol in pos.cli.vols:
                if pos.cli.vol_dict[vol]["status"].lower() == "mounted":
                    assert (
                        pos.cli.unmount_volume(volumename=vol, array_name=array)[0]
                        == True
                    )

                assert (
                    pos.cli.delete_volume(volumename=vol, array_name=array)[0] == True
                )

    # assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


@pytest.mark.sanity
def test_qos_happy_path():
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.list_array()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert (
                pos.cli.create_volume(volumename="vol1", array_name=array, size="1gb")[
                    0
                ]
                == True
            )
            assert (
                pos.cli.create_volume_policy_qos(
                    volumename="vol1", arrayname=array, maxbw="1000", maxiops="1000"
                )[0]
                == True
            )
            assert (
                pos.cli.mount_volume(
                    volumename="vol1",
                    array_name=array,
                    nqn=pos.target_utils.ss_temp_list[0],
                )[0]
                == True
            )
        assert (
            pos.client.nvme_connect(
                pos.target_utils.ss_temp_list[0],
                pos.target_utils.helper.ip_addr[0],
                "1158",
            )
            == True
        )
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
            )[0]
            == True
        )
    except Exception as e:
        logger.error(e)
        pos.exit_handler()


@pytest.mark.sanity
@pytest.mark.parametrize("num_vol", [1, 256])
def test_qos_set_reset(num_vol):
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.list_array()[0] == True
        for index, array in enumerate(list(pos.cli.array_dict.keys())):
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=num_vol, size = "1gb"
                )
                == True
            )
            assert pos.cli.list_volume(array_name=array)[0] == True
            for vol in pos.cli.vols:
                assert (
                    pos.cli.create_volume_policy_qos(
                        volumename=vol,
                        arrayname=array,
                        maxbw="1000000000",
                        maxiops="1000000",
                    )[0]
                    == True
                )
                assert (
                    pos.cli.list_volume_policy_qos(volumename=vol, arrayname=array)[0]
                    == True
                )
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array,
                    volume_list=pos.cli.vols,
                    nqn_list=[pos.target_utils.ss_temp_list[index]],
                )
                == True
            )
        assert (
            pos.client.nvme_connect(
                pos.target_utils.ss_temp_list[0],
                pos.target_utils.helper.ip_addr[0],
                "1158",
            )
            == True
        )
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
            )[0]
            == True
        )
        for vol in pos.cli.vols:
            assert (
                pos.cli.reset_volume_policy_qos(volumename=vol, arrayname=array)[0]
                == True
            )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()


@pytest.mark.sanity
def test_qos_rebuilding_Array():
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.list_array()[0] == True
        for index, array in enumerate(list(pos.cli.array_dict.keys())):
            assert pos.cli.info_array(array_name=array)[0] == True
            assert (
                pos.target_utils.device_hot_remove(
                    device_list=[pos.cli.array_info[array]["data_list"][0]]
                )
                == True
            )
            assert (
                pos.target_utils.create_volume_multiple(array_name=array, num_vol=1)
                == True
            )
            assert pos.cli.list_volume(array_name=array)[0] == True
            for vol in pos.cli.vols:
                assert (
                    pos.cli.create_volume_policy_qos(
                        volumename=vol, arrayname=array, maxbw="10000", maxiops="100000"
                    )[0]
                    == True
                )
                assert (
                    pos.cli.list_volume_policy_qos(volumename=vol, arrayname=array)[0]
                    == True
                )
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array,
                    volume_list=pos.cli.vols,
                    nqn_list=[pos.target_utils.ss_temp_list[index]],
                )
                == True
            )
        assert (
            pos.client.nvme_connect(
                pos.target_utils.ss_temp_list[0],
                pos.target_utils.helper.ip_addr[0],
                "1158",
            )
            == True
        )
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
            )[0]
            == True
        )
        for vol in pos.cli.vols:
            assert (
                pos.cli.reset_volume_policy_qos(volumename=vol, arrayname=array)[0]
                == True
            )

    except Exception as e:
        logger.error(e)
        pos.exit_handler()
