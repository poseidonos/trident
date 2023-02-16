import pytest
import traceback

from common_libs import *
import logger

logger = logger.get_logger(__name__)


array = [("RAID5", 3)]

@pytest.mark.regression
@pytest.mark.parametrize("num_vols", [100])
@pytest.mark.parametrize("array_raid, num_devs", array)
def test_hetero_multi_array_GC(array_fixture, array_raid, num_devs, num_vols):
    """
    Test to create two RAID5 (Default) arrays with 3 (Default) hetero devices.
    Create and mount 100 (Default) volumes from each array. Trigger GC.
    """
    logger.info(
        f" ==================== Test :  test_hetero_multi_array_GC[{array_raid}-{num_devs}-{num_vols}] ================== "
    )
    try:
        pos = array_fixture
        num_array = 2

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list
 
        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for array_index in range(num_array):
            data_disk_req = {'mix': 2, 'any': num_devs - 2}
            assert create_hetero_array(pos, array_raid, data_disk_req,
                                       array_index=array_index, array_mount="WT", 
                                       array_info=True) == True
 
        assert volume_create_and_mount_multiple(pos, num_volumes=num_vols) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        # Run Block IO
        fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write --bs=128k "\
                  f"--iodepth=64 --time_based --runtime=120 --size=2g"

        # Run GC two times to create invalid blocks
        assert pos.client.fio_generic_runner(
                    nvme_devs, fio_user_data=fio_cmd)[0] == True
        assert pos.client.fio_generic_runner(
                    nvme_devs, fio_user_data=fio_cmd)[0] == True

        assert pos.cli.array_list()[0] == True
        for array_name in pos.cli.array_dict.keys():
            assert pos.cli.wbt_do_gc(array_name=array_name)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )
