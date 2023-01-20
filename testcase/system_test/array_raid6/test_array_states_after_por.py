import pytest
import logger

logger = logger.get_logger(__name__)

from common_libs import *

@pytest.mark.parametrize(
    "array1_num_drive, array2_num_drive,por",
    [
        (2, 2, "Spor"),   # SPS-4598
        (1, 2, "Spor"),   # SPS-4597
        (0, 2, "Spor"),   # SPS-4608
        (1, 1, "Spor"),   # SPS-4607
        (2, 3, "Spor"),   # SPS-4606
        (1, 3, "Spor"),   # SPS-4605
        (1, 2, "Npor"),   # SPS-4611
        (0, 2, "Npor"),   # SPS-4610
        (2, 3, "Npor"),   # SPS-4615
    ],
)
def test_post_por_array_state(array_fixture, array1_num_drive, array2_num_drive,por):
    logger.info(
        f" ==================== Test : test_post_{por}_array_state ================== "
    )
    try:
        pos = array_fixture
        assert multi_array_data_setup(data_dict=pos.data_dict, num_array=2,
                                      raid_types=("RAID6","RAID6"),
                                      num_data_disks=(4,4),
                                      num_spare_disk=(array1_num_drive, array2_num_drive),
                                      auto_create=(True, True),
                                      array_mount=("WT", "WT")) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.array_list()[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=pos.cli.array_dict.keys(),
                                                subs_list=pos.target_utils.ss_temp_list) == True
        run_io(pos)

        assert pos.cli.array_list()[0] == True
        array_names = list(pos.cli.array_dict.keys())
        num_drive=[array1_num_drive, array2_num_drive]
        for i,array in enumerate(array_names):
            assert pos.cli.array_info(array_name=array)[0] == True
            data_list = pos.cli.array_data[array]["data_list"]

            assert pos.target_utils.device_hot_remove(data_list[:num_drive[i]]) == True
            assert pos.target_utils.array_rebuild_wait(array_name=array)
            assert pos.cli.array_info(array)[0] == True
            array_status = pos.cli.array_data[array]
            logger.info(array_status["state"])

        pos.client.check_system_memory()
        if por == "Spor":
            assert pos.target_utils.spor(write_through=True) == True
        else:
            assert pos.target_utils.npor() == True

        for array in pos.cli.array_dict.keys():
            assert pos.cli.array_info(array_name=array)[0] == True
            logger.info("{} State : {} and {} Situation : {}".format(array,pos.cli.array_data[array]['state'],array,pos.cli.array_data[array]['situation']))
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.parametrize(
    "array1_num_drive, array2_num_drive",
    [
        (2, 2),   # SPS-4612
        (1, 2),   # SPS-4614
        (1, 3),   # SPS-4613
    ],
)
def test_post_por_array_state_mulitple(array_fixture,array1_num_drive, array2_num_drive):
    logger.info(
        f" ==================== Test : test_post_por_array_state_mulitple ================== "
    )
    try:
        pos = array_fixture
        assert multi_array_data_setup(data_dict=pos.data_dict, num_array=2,
                                      raid_types=("RAID6","RAID6"),
                                      num_data_disks=(4,4),
                                      num_spare_disk=(1,1),
                                      auto_create=(True, True),
                                      array_mount=("WT", "WT")) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=pos.cli.array_dict.keys(),
                                                subs_list=pos.target_utils.ss_temp_list) == True

        run_io(pos)

        assert pos.cli.array_list()[0] == True
        array_names = list(pos.cli.array_dict.keys())
        num_drive=[array1_num_drive, array2_num_drive]
        for i,array in enumerate(array_names):
            assert pos.cli.array_info(array_name=array)[0] == True
            data_list = pos.cli.array_data[array]["data_list"]

            assert pos.target_utils.device_hot_remove(data_list[:num_drive[i]]) == True
            assert pos.target_utils.array_rebuild_wait(array_name=array)
            assert pos.cli.array_info(array)[0] == True
            array_status = pos.cli.array_data[array]
            logger.info(array_status["state"])

        pos.client.check_system_memory()
        for index  in range(5):
            assert pos.target_utils.spor() == True

            assert pos.target_utils.npor() == True

            for array in pos.cli.array_dict.keys():
                assert pos.cli.array_info(array_name=array)[0] == True
                logger.info("{} State : {} and {} Situation : {}".format(array,
                                     pos.cli.array_data[array]['state'], array,
                                     pos.cli.array_data[array]['situation']))
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
