import pytest
import traceback

import time 
from common_libs import *

import logger
logger = logger.get_logger(__name__)

test_params = {
        "t0":  ("RAID5",  3,  "wt", "RAID5",  3,  "wt", "block", 60),
        "t1":  ("RAID5",  3,  "wt", "RAID5",  3,  "wt", "file", 60),
        "t2":  ("RAID5",  16, "wb", "RAID5",  16, "wb", "block", 60),
        "t3":  ("RAID5",  16, "wb", "RAID5",  16, "wt", "file", 60),
        "t4":  ("RAID0",  2,  "wt", "RAID0",  4,  "wb", "file", 60),
        "t5":  ("RAID10", 4,  "wb", "RAID10", 4,  "wb", "block", 60),
        "t6":  ("RAID0",  2,  "wb", "RAID0",  2,  "wb", "file", 60),
        "t7":  ("RAID0",  2,  "wb", "RAID0",  2,  "wb", "block", 60),
        "t8":  ("RAID10", 4,  "wb", "RAID10", 4,  "wb", "block", 60),
        "t9":  ("RAID0",  2,  "wb", "RAID0",  2,  "wb", "block", 60),
        "t10": ("RAID5",  3,  "wb", "RAID5",  3,  "wb", "file", 60),
        "t11": ("RAID5",  3,  "wb", "RAID5",  6,  "wb", "file", 60),
        "t12": ("RAID5",  3,  "wb", "RAID5",  6,  "wb", "block", 60),
        }

@pytest.mark.regression
@pytest.mark.parametrize("test_id", test_params)
def test_hetero_multi_array_max_size_volume_FIO(array_fixture, test_id):
    """
    Test two arrays using hetero devices, Create max size volume on each array.
    Run File or Block FIO.
    """
    logger.info(
        f" ==================== Test : test_hetero_multi_array_max_size_volume_FIO[{test_id}] ================== "
    )
    try:
        pos = array_fixture

        array1_raid, array1_devs, array1_mount = test_params[test_id][:3]
        array2_raid, array2_devs, array2_mount = test_params[test_id][3:6] 
        io_type, fio_runtime = test_params[test_id][6:8]
        raid_types = (array1_raid, array2_raid)
        num_devs = (array1_devs, array2_devs)
        mount_types = (array1_mount, array2_mount)

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list
 
        # Loop 2 times to create two RAID array of RAID5 using hetero device
        for array_index in range(2):
            data_disk_req = {'mix': 2, 
                             'any': num_devs[array_index] - 2}
            assert create_hetero_array(pos, raid_types[array_index], 
                                       data_disk_req, array_index=array_index,
                                       array_mount=mount_types[array_index], 
                                       array_info=True) == True
 
        assert volume_create_and_mount_multiple(pos, num_volumes=1) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        # Run File IO or Block IO
        fio_cmd = f"fio --name=seq_write --ioengine=libaio --rw=write --bs=128k "\
                  f"--iodepth=64 --time_based --runtime={fio_runtime} --size=10g"

        assert run_fio_all_volumes(pos, fio_cmd=fio_cmd, fio_type=io_type, run_async=False) == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)

    logger.info(
        " ============================= Test ENDs ======================================"
    )


array = [("RAID5", 3)]
@pytest.mark.parametrize("additional_ops", ["no", "npor", "vol_del_reverse"])
@pytest.mark.parametrize("raid_type, num_disk", array)
def test_hetero_multi_array_512_volume_mix_FIO(array_fixture, raid_type, num_disk, additional_ops):
    """
    Test two RAID5 arrays using hetero devices, Create 256 volumes on each array.
    Run File and Block FIO.
    """
    logger.info(
        " ==================== Test : test_hetero_multi_array_512_volume_mix_FIO ================== "
    )
    try:
        pos = array_fixture
        assert pos.target_utils.get_subsystems_list() == True

        repeat_ops = 1 if additional_ops == "no" else 5
        num_array = 2
        fio_runtime = 120  # FIO for 2 minutes
        mount_point = None
        subs_list = pos.target_utils.ss_temp_list

        for counter in range(repeat_ops):
            # Loop 2 times to create two RAID array of RAID5 using hetero device
            for array_index in range(num_array):
                data_disk_req = {'mix': 2, 'any': num_disk - 2}
                assert create_hetero_array(pos, raid_type, data_disk_req, array_mount="WT", 
                                           array_index=array_index, array_info=True) == True
 
            assert volume_create_and_mount_multiple(pos, num_volumes=256) == True

            # Connect client
            ip_addr = pos.target_utils.helper.ip_addr[0]
            for nqn in subs_list:
                assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True
         
            # Run File IO or Block IO
            fio_cmd = f"fio --name=rand_write --ioengine=libaio --rw=randwrite --bs=128k "\
                      f"--iodepth=64 --time_based --runtime={fio_runtime} --size=2g"
           
            assert run_fio_all_volumes(pos, fio_cmd=fio_cmd, fio_type="mix") == True

            if repeat_ops > 1:
                if pos.client.ctrlr_list()[1]:
                    assert pos.client.nvme_disconnect(subs_list) == True
                assert pos.cli.array_list()[0] == True
                if additional_ops == "npor":
                    # Perform NPOR
                    assert pos.target_utils.npor() == True
                elif additional_ops == "vol_del_reverse" :
                    for array in pos.cli.array_dict.keys():
                        # Delete volumes in reverse order
                        assert pos.cli.volume_list(array_name=array)[0] == True
                        for vol in pos.cli.vols[::-1]:
                            assert pos.cli.volume_unmount(vol, array_name=array)[0] == True
                            assert pos.cli.volume_delete(vol, array_name=array)[0] == True
                # Delete both array Array     
                for array in pos.cli.array_dict.keys():
                    assert pos.cli.array_unmount(array_name=array)[0] == True
                    assert pos.cli.array_delete(array_name=array)[0] == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        if mount_point:
            pos.client.unmount_FS(mount_point)

        traceback.print_exc()
        pos.exit_handler(expected=False)
    
    logger.info(
        " ============================= Test ENDs ======================================"
    )
