import pytest

from pos import POS

import logger

logger = logger.get_logger(__name__)

def test_npor_with_half_uram(system_fixture):
    """Test to perform NPOR with different uram
    Returns:
        bool
    """
    logger.info("================ test_npor_with_half_uram ================")
    try:
        pos = system_fixture
        data_dict = pos.data_dict
        assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.array_list()[0] == True
        for array in pos.cli.array_dict.keys():
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.volume_list(array_name=array)[0] == True
                for vol in pos.cli.vols:
                    if pos.cli.vol_dict[vol]["status"].lower() == "mounted":
                        pos.cli.volume_unmount(volumename=vol, array_name=array)[
                            0
                        ] == True

        assert pos.cli.pos_stop()[0] == True
        assert pos.cli.pos_start()[0] == True
        uram_list = pos.data_dict["device"]["uram"]

        for uram in uram_list:
            uram_name = uram["uram_name"]
            uram_size = int(int(uram["bufer_size"]) // 2)
            assert (
                pos.cli.device_create(
                    uram_name=uram_name, bufer_size=uram_size, strip_size="512"
                )[0]
                == True
            )

        assert pos.cli.device_scan()[0] == True
        assert pos.cli.array_list()[0] == True
        for array in pos.cli.array_dict.keys():
            assert pos.cli.array_mount(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.cli.volume_list(array_name=array)[0] == True
            for vol in pos.cli.vols:
                assert (
                    pos.cli.volume_mount(
                        volumename=vol, array_name=array, nqn=ss_list[0]
                    )[0]
                    == True
                )
    except Exception as e:
        logger.error(f"NPOR failed due to {e}")
        pos.exit_handler(expected=False)
