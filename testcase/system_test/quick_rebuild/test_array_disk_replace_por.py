from time import sleep
import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)


test_por_operations = {
    "t0": (("RAID5", "RAID5"), ("SPOR",)),  
    "t1": (("RAID6", "RAID6"), ("SPOR",)),
    "t2": (("RAID10", "RAID10"), ("SPOR",)),
    
    "t3": (("RAID5", "RAID5",), ("NPOR",)),
    "t4": (("RAID6", "RAID6"), ("NPOR",)),
    "t5": (("RAID10", "RAID10"), ("NPOR",)),

    "t6": (("RAID5", "RAID6"), ("SPOR", "NPOR")),
    "t7": (("RAID6", "RAID10"), ("SPOR", "NPOR")),
    "t8": (("RAID10", "RAID5"), ("SPOR", "NPOR")),  

    "t9": (("RAID5", "RAID6"), ("NPOR", "SPOR")),
    "t10": (("RAID10", "RAID6"), ("NPOR", "SPOR")),

    "t11": (("RAID10", "RAID6"), ("NPOR", "NPOR", "SPOR", "SPOR", "NPOR")),
    "t12": (("RAID10", "RAID5"), ("SPOR", "SPOR", "NPOR", "NPOR", "SPOR")),
    }

@pytest.mark.parametrize("por_operation", test_por_operations)
def test_arrays_disk_replace_por(array_fixture, por_operation):
    """
    The purpose of this test is to create a NO-RAID array with 1 data drive.   
    Verification: POS CLI
    """
    logger.info(
        f" ==================== Test : test_arrays_disk_replace_por[{por_operation}] ================== "
    )
    pos = array_fixture
    try:
        arrays_raid = test_por_operations[por_operation][0]
        por_list = test_por_operations[por_operation][1]
        num_vols = 8

        arrays_data_disks = tuple(RAID_MIN_DISK_REQ_DICT[raid] for raid in arrays_raid)

        assert multi_array_data_setup(pos.data_dict, len(arrays_raid), arrays_raid, 
                    arrays_data_disks, (2, 2), ("WT", "WB"), (False, False)) == True

        assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True

        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert volume_create_and_mount_multiple(pos, num_vols, 
                            array_list=array_list, subs_list=subs_list) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = "fio --name=seq_write --ioengine=libaio --rw=write --iodepth=64 --bs=128k "\
                  "--size=50gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        for por in por_list:
            assert do_por(pos, por) == True

            # Array disk replace
            assert array_disk_remove_replace(pos, array_list, replace=True) == True

            # Add Spare disk
            assert array_add_spare_disk(pos, array_list)== True

        fio_cmd = "fio --name=seq_read --ioengine=libaio --rw=read --iodepth=64 --bs=128k "\
                  "--size=20gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def do_por(pos, por):
    try:
        if (por.lower() == "spor"):
            assert pos.target_utils.spor() == True
        elif (por.lower() == "npor"):
            assert pos.target_utils.npor() == True
        return True
    except Exception as e:
        logger.error(f"Failed to {por} due to {e}")
        return False
