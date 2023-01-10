import pytest

from pos import POS
from common_raid6_api import *

import logger
logger = logger.get_logger(__name__)

import common_libs as setup
@pytest.fixture(scope="module")
def pos_connection():
    logger.info("========= SETUP MODULE ========")
    pos = POS()

    yield pos

    

    logger.info("========= CLEANUP MODULE ========")
    del pos

@pytest.fixture(scope="function")
def journal_setup_cleanup(pos_connection):
    logger.info("========== SETUP TEST =========")
    pos = pos_connection
    if not pos.target_utils.helper.check_pos_exit():
        assert pos.cli.system_stop()[0] == True

    data_dict = pos.data_dict
    data_dict['system']['phase'] = "true"
    data_dict['subsystem']['phase'] = "true"
    data_dict['device']['phase'] = "true"

    yield pos

    logger.info("========== CLEANUP AFTER TEST =========")

    assert pos_system_restore_stop(pos) == True
    assert pos.pos_conf.restore_config() == True

    logger.info("==========================================")

def pos_bringup(pos):
    try:
        data_dict = pos.data_dict
        data_dict['array']['phase'] = "false"
        data_dict['volume']['phase'] = "false"
        assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

        data_dict['system']['phase'] = "false"
        data_dict['subsystem']['phase'] = "false"
        data_dict['device']['phase'] = "false"
        data_dict['array']['phase'] = "true"
        return True
    except Exception as e:
        logger.error(f"Failed to bringup pos due to {e}")
        return False


# Num of Volumes, IO (Write, Rand Write, Read, Random Read))
jouranl_enable = [True, False]
@pytest.mark.parametrize("jouranl_enable", jouranl_enable)
@pytest.mark.parametrize("raid_type", ARRAY_ALL_RAID_LIST)
def test_raid6_arrays_journal_enable(journal_setup_cleanup, raid_type, jouranl_enable):
    """
    The purpose of this test is to create two arrays and atleast 1 should be RAID 6. 
    Create and mount multiple volumes to each array and utilize its full capacity.  
    Run File IO, Block IO and Mix of File and Block IO.
    Verification: POS CLI, End to End Data Flow, Data Integrity
    """
    logger.info(
        f" ==================== Test : test_raid6_arrays_journal_enable[{raid_type}-{jouranl_enable}] ================== "
    )
    pos = journal_setup_cleanup
    try:
        assert pos.pos_conf.journal_state(enable=jouranl_enable,
                                          update_now=True) == True

        assert pos_bringup(pos) == True

        num_vols = 8
        num_disk = RAID_MIN_DISK_REQ_DICT[raid_type]
        arrays_num_disks = (RAID6_MIN_DISKS, num_disk)
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < sum(arrays_num_disks):
            pytest.skip("Less number of data disk")

        assert multi_array_data_setup(pos.data_dict, 2, ("RAID6", raid_type), 
                                      arrays_num_disks, (0, 0), ("WT", "WB"),
                                      (False, False)) == True
        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert volume_create_and_mount_multiple(pos, num_vols) == True
        subs_list = pos.target_utils.ss_temp_list

        assert vol_connect_and_run_random_io(pos, subs_list, '50gb') == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.parametrize("por",["NPOR","SPOR"])
def test_raid6_longetivity_npor_spor_journal_enabled(journal_setup_cleanup,por):
    '''
    The purpose of this testcase is to test NPOR and SPOR scenarios with journal enabled
    '''
    logger.info(
        f" ==================== Test : test_raid6_longetivity_with_spor_journal_enabled[{por}] ================== "
    )
    pos = journal_setup_cleanup
    try:
        assert pos.pos_conf.journal_state(enable=True,update_now=True) == True
        assert pos_bringup(pos) == True
        assert multi_array_data_setup(data_dict = pos.data_dict,num_array = 2,
                                      raid_types = ("RAID6","RAID6"),num_data_disks=(4,4),
                                      num_spare_disk=(1,1),auto_create=(True,True),array_mount=("WT","WT")) == True
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=pos.cli.array_dict.keys(),
                                                      subs_list=pos.target_utils.ss_temp_list) == True

        assert setup.nvme_connect(pos=pos)[0] == True
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw={} --iodepth=64 --direct=1 --numjobs=1 --bs=64k --verify=md5"
        assert setup.run_fio_all_volumes(pos=pos,nvme_devs=pos.client.nvme_list_out,fio_cmd=fio_cmd,size='10g') == True
        if por == "NPOR":
            assert pos.target_utils.Npor() == True
        else:
            assert pos.target_utils.Spor(uram_backup=False,write_through=True) == True

        for array in pos.cli.array_dict.keys():
            disk_interval = [(0,)]
            assert array_disks_hot_remove(pos=pos,array_name=array,disk_remove_interval_list=disk_interval) == True
            assert pos.cli.array_info(array_name=array)[0] == True
            logger.info("{} State : {} and {} Situation : {}".format(array,pos.cli.array_data[array]['state'],array,pos.cli.array_data[array]['situation']))
            assert pos.cli.array_data[array]['state'] == 'BUSY' and pos.cli.array_data[array]['situation'] == 'REBUILDING'

        assert setup.run_fio_all_volumes(pos=pos, nvme_devs=pos.client.nvme_list_out, fio_cmd=fio_cmd,size='5g') == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")

        pos.exit_handler(expected=False)