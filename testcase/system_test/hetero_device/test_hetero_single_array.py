import pytest
import traceback

import logger

logger = logger.get_logger(__name__)

@pytest.mark.regression
def test_hetero_single_array_mount(array_fixture):
    """
    Create one RAID5 array using hetero devices and mount
    """
    logger.info(
        " ==================== Test : test_hetero_single_array_mount ================== "
    )
    try:
        pos = array_fixture
        if len(pos.cli.system_disks) < 3:
            pytest.skip(f"Insufficient disk count {len(pos.cli.system_disks)}. "\
                        f"Required minimum 3 disk to create RAID5 array")

        array_name = "array1"
        uram_name = data_dict["device"]["uram"][0]["uram_name"]

        data_device_conf = {'mix': 2, 'any': 1}

        if not pos.target_utils.get_hetero_device(data_device_conf):
            logger.info("Failed to get the required hetero devcies")
            pytest.skip("Required condition not met. Refer to logs for more details")

        data_drives = pos.target_utils.data_drives
        spare_drives = pos.target_utils.spare_drives

        assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                    spare=spare_drives, raid_type="RAID5",
                                    array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
