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
    assert pos.cli.list_array()[0] == True
    for array_name in pos.cli.array_dict.keys():
        assert pos.cli.array_info(array_name=array_name)[0] == True
        if pos.cli.array_dict[array_name].lower() == "mounted":
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol in pos.cli.vols:
                assert (
                    pos.cli.volume_info(array_name=array_name, vol_name=vol)[0] == True
                )

                if pos.cli.volume_info[array_name][vol]["status"] == "Mounted":
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
@pytest.mark.parametrize("num_vols", [(256, 257), (257, 257)])
def test_unsupported_volumes(num_vols):
    """
    The purpose of test is to try to create 513 volumes (256 array 1, 257 array 2) and
    514 volumes (257 array 1, 257 array 2).
    """
    try:
        logger.info(
            f"================ Test: test_unsupported_volumes[{num_vols}] ================"
        )
        assert pos.target_utils.get_subsystems_list() == True
        subsystem_list = pos.target_utils.ss_temp_list
        assert pos.cli.list_array()[0] == True
        for index, array_name in enumerate(pos.cli.array_dict.keys()):
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_info[array_name].get("size"))
            vol_size = f"{int(array_size // (1024 * 1024)/ 260)}mb"  # Volume Size in MB
            assert (
                pos.target_utils.create_volume_multiple(array_name, 256, size=vol_size)
                == True
            )
            if (num_vols[index] - 256) > 0:
                # Create and mount 257 volumes
                vol_name = f"{array_name}_PoS_VoL_257"
                assert pos.cli.volume_create(vol_name, vol_size, array_name)[0] == False

            assert pos.cli.volume_list(array_name=array_name)[0] == True
            assert len(pos.cli.vols) == 256
            ss_list = [ss for ss in subsystem_list if array_name in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name, pos.cli.vols, ss_list[0]
                )
                == True
            )

        logger.info("=============== TEST ENDs ================")

    except Exception as e:
        logger.info(f" Test Script failed due to {e}")
        pos.exit_handler(expected=False)
