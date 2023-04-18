import pytest

from traceback import print_exc
from common_libs import *
import time

import logger
logger = logger.get_logger(__name__)

def array_volume_setup(pos, arrays_raid, arrays_disk, num_volumes):
    pos.data_dict["array"]["pos_array"][0]["raid_type"] = arrays_raid[0]
    pos.data_dict["array"]["pos_array"][1]["raid_type"] = arrays_raid[1]
    
    pos.data_dict["array"]["pos_array"][0]["data_device"] = arrays_disk[0]
    pos.data_dict["array"]["pos_array"][1]["data_device"] = arrays_disk[1]

    pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = num_volumes[0]
    pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = num_volumes[1]
    
    assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
    assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True

def volume_fill_wait(pos, array_names, vol_filled):
    # Wait for async FIO completions
    sleep_time = 30 # seconds
    while True:
        for array_name in array_names:
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            vol_curr_filled = []
            for vol_name, vol_data in pos.cli.vol_dict.items():
                logger.info(f"Volume: {vol_name} ({vol_data['filled']}%)")
                vol_curr_filled.append(int(vol_data["filled"]))

        min_filled = min(vol_curr_filled)
        if min_filled > vol_filled :
            logger.info(f"Volume is filled required limit {vol_filled}")
            break

        logger.info(f"Volume is yet to filled {vol_filled}. Wait {sleep_time} sec...")
        time.sleep(sleep_time)  # Wait for 30 seconds


fio_params = {
    'A' : {'bs': '128k', 'iodepth': 64,  'numjobs': 8, 'rw': 'randwrite'},
    'B' : {'bs': '128k', 'iodepth': 128, 'numjobs': 8, 'rw': 'randwrite'}
}

test_param1 = {
    # Test ID   (Arrays RAID)   (Num Disks)  (Num Volumes)  Vol Percent     FIO Params
    't0' : [("RAID5", "RAID6"),    (4, 4),     (2, 2),       20,         fio_params['A']],
    't1' : [("RAID5", "RAID6"),    (4, 4),     (2, 2),       10,         fio_params['B']],
    't2' : [("RAID5", "RAID10"),   (4, 4),     (2, 2),       50,         fio_params['B']],
    't3' : [("RAID5", "RAID10"),   (4, 4),     (2, 2),       80,         fio_params['A']]
}

@pytest.mark.regression
@pytest.mark.parametrize("test_id", test_param1)
def test_live_io_spor(array_fixture, test_id):
    """
    The purpose of this test case is to create arrays and volumes of selected
    type. Run IO to all volumes, Then perform the SPOR sequence when volume is
    all volumes are filled upto selected Vol Percent.
    """
    logger.info(
        f" ==================== Test : test_live_io_spor[{test_id}] ================== "
    )
    try:
        pos = array_fixture
        arrays_raid = test_param1[test_id][0]
        arrays_disk = test_param1[test_id][1]
        num_volumes = test_param1[test_id][2]
        vol_filled = test_param1[test_id][3]
        fio = test_param1[test_id][4]

        logger.info(f"test_param1[test_id] : {test_param1[test_id]}")
        logger.info(f"fio : {fio}")

        fio_temp = "fio --name=test_{} --ioengine=libaio --rw={} --iodepth={} --direct=1 --bs={} --numjobs={} --size=100%"
        fio_cmd = fio_temp.format(fio['rw'], fio['rw'], fio['iodepth'],
                                  fio['bs'], fio['numjobs'])

        logger.info(f"fio_cmd {fio_cmd}")

        array_volume_setup(pos, arrays_raid, arrays_disk, num_volumes)

        assert pos.cli.array_list()[0] == True
        array_names = list(pos.cli.array_dict.keys())

        assert pos.target_utils.get_subsystems_list() == True
        # Connect client
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True

        # Run IO
        pos.client.check_system_memory()
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        block_io_devs = nvme_devs
        io_mode = True  # Set False this to Block IO
        fio_temp = "fio --name=test_{} --ioengine=libaio --rw={} --iodepth={} --direct=1 --bs={} --numjobs={} --size=100%"
        fio_cmd = fio_temp.format(fio['rw'], fio['rw'], fio['iodepth'],
                                  fio['bs'], fio['numjobs'])
        out, async_block_io = pos.client.fio_generic_runner(
                                    block_io_devs, fio_user_data=fio_cmd,
                                    IO_mode=io_mode, run_async=True)
        assert out == True

        # Wait for async FIO completions
        volume_fill_wait(pos, array_names, vol_filled)
           
        # Perfrom SPOR
        assert pos.target_utils.spor(uram_backup=False) == True

        # Disconnect Subystems
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

        # Block IO Stopped
        counter = 10
        while counter > 0:
            if not async_block_io.is_complete():
                logger.info(f"Block IO is still running. Wait {sleep_time} seconds...")
                time.sleep(sleep_time)
                continue

            counter = counter - 1

        pos.client.check_system_memory()
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)


test_param2 = {
    # Test |  Array1 and       |   Data   |  Num Of  | Vol % |  Overwrite |  FIO Params      #
    # ID   |  Array2 RAID)     |   Disks  |  Vols    | @SPOR |  IO Size   |  for both Writes #
    't0' : [("RAID5", "RAID6"),   (4, 4),   (2, 2),       20,    "5%",       fio_params['A']],
    't1' : [("RAID5", "RAID6"),   (4, 4),   (2, 2),       10,    "5%",       fio_params['B']],
    't2' : [("RAID5", "RAID10"),  (4, 4),   (2, 2),       40,    "25%",      fio_params['B']]
}

@pytest.mark.regression
@pytest.mark.parametrize("test_id", test_param2)
def test_overwrite_live_io_spor(array_fixture, test_id):
    """
    The purpose of this test case is to create arrays and volumes of selected
    type. Run IO upto selected limit, then start overwrite IO to all volumes. 
    Perform SPOR sequence when all volumes are filled upto selected Vol Percent.
    """
    logger.info(
        f" ==================== Test : test_live_io_spor[{test_id}] ================== "
    )
    try:
        pos = array_fixture
        arrays_raid = test_param2[test_id][0]
        arrays_disk = test_param2[test_id][1]
        num_volumes = test_param2[test_id][2]
        vol_filled = test_param2[test_id][3]
        overwrite_io = test_param2[test_id][4]
        fio = test_param2[test_id][5]

        array_volume_setup(pos, arrays_raid, arrays_disk, num_volumes)

        assert pos.cli.array_list()[0] == True
        array_names = list(pos.cli.array_dict.keys())

        assert pos.target_utils.get_subsystems_list() == True
        # Connect client
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True

        # Run IO
        pos.client.check_system_memory()
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        block_io_devs = nvme_devs
        io_mode = True  # Set False this to Block IO
        fio_temp = "fio --name=test_{} --ioengine=libaio --rw={} --iodepth={} --direct=1 --bs={} --numjobs={} --size={}"

        # IO before overwrite
        fio_cmd = fio_temp.format(fio['rw'], fio['rw'], fio['iodepth'],
                                  fio['bs'], fio['numjobs'], overwrite_io)
        assert pos.client.fio_generic_runner(block_io_devs,
                     fio_user_data=fio_cmd, IO_mode=io_mode)[0] == True
        
        for array_name in array_names:
            assert pos.cli.volume_list(array_name=array_name)[0] == True
            for vol_name, vol_data in pos.cli.vol_dict.items():
                logger.info(f"Volume: {vol_name} ({vol_data['filled']}%)")


        # Overwrite IO
        logger.info("IO Overwrite Started...")
        fio_cmd = fio_temp.format(fio['rw'], fio['rw'], fio['iodepth'],
                                  fio['bs'], fio['numjobs'], "100%")
        out, async_block_io = pos.client.fio_generic_runner(
                                    block_io_devs, fio_user_data=fio_cmd,
                                    IO_mode=io_mode, run_async=True)
        assert out == True

        # Wait for volume filled by requested percent
        volume_fill_wait(pos, array_names, vol_filled)
           
        # Perfrom SPOR
        assert pos.target_utils.spor(uram_backup=False) == True

        # Disconnect Subystems
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

        # Block IO Stopped
        counter = 10
        while counter > 0:
            if not async_block_io.is_complete():
                logger.info(f"Block IO is still running. Wait {sleep_time} seconds...")
                time.sleep(sleep_time)
                continue

            counter = counter - 1

        pos.client.check_system_memory()
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)


fio_temp = "fio --name=test_{} --ioengine=libaio --rw={} --iodepth={} --direct=1 --bs={} --numjobs={} --size={}"

test_param3 = {
    # Test |  Array1 and       |   Data   |  Num Of  | Vol % |  Disk Fail  |  FIO Params      #
    # ID   |  Array2 RAID)     |   Disks  |  Vols    | @SPOR |  Vol Filled |  for both Writes #
    't0' : [("RAID5", "RAID6"),   (4, 4),   (2, 2),       20,    10,         fio_params['A']],
    't1' : [("RAID5", "RAID6"),   (4, 4),   (2, 2),       10,    5,          fio_params['B']],
    't2' : [("RAID5", "RAID6"),   (4, 4),   (2, 2),       6,     3,          fio_params['B']],
    't3' : [("RAID5", "RAID10"),  (4, 4),   (2, 2),       80,    30,         fio_params['B']]
}

@pytest.mark.regression
@pytest.mark.parametrize("test_id", test_param3)
def test_rebuild_live_io_spor(array_fixture, test_id):
    """
    The purpose of this test case is to create arrays and volumes of selected
    type. Run IO, when volume is filled upto selected limit, fail data disk to
    both arrays and wait for Rebuild to complete upto 10%. Then perform SPOR 
    sequence when all volumes are filled upto selected Vol Percent.
    """
    logger.info(
        f" ==================== Test : test_rebuild_live_io_spor[{test_id}] ================== "
    )
    try:
        pos = array_fixture
        arrays_raid = test_param3[test_id][0]
        arrays_disk = test_param3[test_id][1]
        num_volumes = test_param3[test_id][2]
        spor_vol_filled = test_param3[test_id][3]
        rebuild_vol_filled = test_param3[test_id][4]
        fio = test_param3[test_id][5]

        pos.data_dict["array"]["pos_array"][0]["spare_device"] = 1
        pos.data_dict["array"]["pos_array"][1]["spare_device"] = 1

        array_volume_setup(pos, arrays_raid, arrays_disk, num_volumes)

        assert pos.cli.array_list()[0] == True
        array_names = list(pos.cli.array_dict.keys())

        assert pos.target_utils.get_subsystems_list() == True
        # Connect client
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True

        # Run IO
        pos.client.check_system_memory()
        nvme_devs = pos.client.nvme_list_out

        # Run File IO and Block IO Parallely
        block_io_devs = nvme_devs
        io_mode = True  # Set False this to Block IO

        # IO Start
        fio_cmd = fio_temp.format(fio['rw'], fio['rw'], fio['iodepth'],
                                  fio['bs'], fio['numjobs'], "100%")
        out, async_block_io = pos.client.fio_generic_runner(
                                    block_io_devs, fio_user_data=fio_cmd,
                                    IO_mode=io_mode, run_async=True)
        assert out == True

        # Wait for volume filled by requested percent before Hot Remove
        volume_fill_wait(pos, array_names, rebuild_vol_filled)

        # Array Rebuild
        assert array_disks_hot_remove(pos, array_names[0],[(5,)]) == True
        assert array_disks_hot_remove(pos, array_names[1],[(10,)]) == True

        # Wait for volume filled by requested percent before Hot Remove
        volume_fill_wait(pos, array_names, spor_vol_filled)
           
        # Perfrom SPOR
        assert pos.target_utils.spor(uram_backup=False) == True

        # Disconnect Subystems
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

        # Block IO Stopped
        counter = 10
        while counter > 0:
            if not async_block_io.is_complete():
                logger.info(f"Block IO is still running. Wait {sleep_time} seconds...")
                time.sleep(sleep_time)
                continue

            counter = counter - 1

        pos.client.check_system_memory()
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        pos.exit_handler(expected=False)
