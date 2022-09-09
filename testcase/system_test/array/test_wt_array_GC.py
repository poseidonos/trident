import pytest
from array_test_common import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("no-raid", 1), ("RAID0", 2), ("RAID10", 4),("RAID5",4)]
)
def test_wt_array_GC(setup_cleanup_array_function, raid_type, nr_data_drives):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(" ==================== Test : test_wt_array_GC ================== ")
    try:
        pos = setup_cleanup_array_function
        nr_spare_drives = 1
        if raid_type in ["no-raid", "RAID0"]:
            nr_spare_drives = 0
        assert wt_array_setup(pos, raid_type, 
                              nr_data_drives, nr_spare_drives) == True
        array_name = pos.data_dict['array']['pos_array'][0]["array_name"]

        assert (
            pos.cli.create_volume("pos_vol_1", array_name=array_name, size="2000gb")[0]
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem1" in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        for sync in [True, False]:
            assert (
                pos.client.fio_generic_runner(
                    pos.client.nvme_list_out,
                    fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=300",
                    run_async=sync,
                )[0]
                == True
            )

        assert pos.cli.wbt_do_gc()[0] == False
        assert pos.cli.wbt_get_gc_status()[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
