import pytest

import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression
@pytest.mark.parametrize("num_vols", [(256, 257), (257, 257)])
def test_unsupported_volumes(volume_fixture, num_vols):
    """
    The purpose of test is to try to create 513 volumes (256 array 1, 257 array 2) and
    514 volumes (257 array 1, 257 array 2).
    """
    try:
        logger.info(
            f"================ Test: test_unsupported_volumes[{num_vols}] ================"
        )
        pos = volume_fixture
        assert pos.target_utils.get_subsystems_list() == True
        subsystem_list = pos.target_utils.ss_temp_list
        assert pos.cli.array_list()[0] == True
        for index, array_name in enumerate(pos.cli.array_dict.keys()):
            assert pos.cli.array_info(array_name=array_name)[0] == True
            array_size = int(pos.cli.array_data[array_name].get("size"))
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
