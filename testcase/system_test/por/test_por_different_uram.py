import pytest

from pos import POS

import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


def test_npor_with_half_uram():
    """Test to perform NPOR with different uram
    Returns:
        bool
    """
    logger.info("================ test_npor_with_half_uram ================")
    try:
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_array()[0] == True
        for array in pos.cli.array_dict.keys():
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.list_volume(array_name=array)[0] == True
                for vol in pos.cli.vols:
                    if pos.cli.vol_dict[vol]["status"].lower() == "mounted":
                        pos.cli.unmount_volume(volumename=vol, array_name=array)[
                            0
                        ] == True

        assert pos.cli.stop_system()[0] == True
        assert pos.cli.start_system()[0] == True
        uram_list = pos.data_dict["device"]["uram"]

        for uram in uram_list:
            uram_name = uram["uram_name"]
            uram_size = int(int(uram["bufer_size"]) // 2)
            assert (
                pos.cli.create_device(
                    uram_name=uram_name, bufer_size=uram_size, strip_size="512"
                )[0]
                == True
            )

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_array()[0] == True
        for array in pos.cli.array_dict.keys():
            assert pos.cli.mount_array(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.cli.list_volume(array_name=array)[0] == True
            for vol in pos.cli.vols:
                assert (
                    pos.cli.mount_volume(
                        volumename=vol, array_name=array, nqn=ss_list[0]
                    )[0]
                    == True
                )
    except Exception as e:
        logger.error(f"NPOR failed due to {e}")
        pos.exit_handler(expected=False)
