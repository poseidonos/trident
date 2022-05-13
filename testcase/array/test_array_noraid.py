import pytest

# from lib.pos import POS
import logger
from pos import POS

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict
    raid_type = "no-raid"
    pos = POS()
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    data_dict = pos.data_dict
    data_dict["system"]["phase"] = "true"
    data_dict["device"]["phase"] = "true"
    data_dict["array"]["phase"] = "false"
    data_dict["subsystem"]["phase"] = "true"
    data_dict["volume"]["array1"]["phase"] = "false"
    data_dict["volume"]["array2"]["phase"] = "false"

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
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


def test_NoRaidArray_256Volumes_BlockIO():
    try:

        data_dict["system"]["phase"] = "false"
        data_dict["device"]["phase"] = "false"
        data_dict["subsystem"]["phase"] = "false"
        data_dict["array"]["phase"] = "true"
        data_dict["volume"]["array1"]["num_vol"] = 256
        data_dict["volume"]["array1"]["phase"] = "true"
        data_dict["array"]["num_array"] = 1
        data_dict["array"]["array1_data_count"] = 1
        data_dict["array"]["array1_raid_type"] = raid_type

        assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
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
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def test_Autocreate_NoRaid_Array():
    try:
        assert pos.cli.list_device()[0] == True
        assert (
            pos.cli.autocreate_array(
                buffer_name=pos.cli.dev_type["NVRAM"][0],
                num_data="1",
                num_spare="0",
                array_name="array1",
                raid="no-raid",
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name="array1")[0] == True
        assert (
            pos.target_utils.create_volume_multiple(
                array_name="array1", num_vol=2, size="500gb"
            )
            == True
        )
        assert pos.cli.list_volume("array1")[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name="array1",
                volume_list=pos.cli.vols,
                nqn_list=[pos.target_utils.ss_temp_list[0]],
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
    except Exception as e:
        logger.error(e)
        pos.exit_handler()
