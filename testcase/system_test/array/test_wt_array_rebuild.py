import pytest

from pos import POS
import logger
import random
import time

# from pos import POS

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("wt_array.json")
    data_dict = pos.data_dict
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    assert pos.target_utils.pci_rescan() == True

    # assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives", 
                         [("RAID5", 3), ("RAID10", 2), ("RAID10", 4)])
def test_wt_array_rebuild_after_BlockIO(raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}")
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = [system_disks.pop()]

        array_name = "array1"
        assert pos.cli.create_array(write_buffer="uram0", data=data_disk_list,
                                    spare=spare_disk_list, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True
        assert pos.cli.create_volume("pos_vol1", array_name=array_name, size="1gb")[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                            volume_list=pos.cli.vols, nqn_list=ss_list) == True

        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, 
                            pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=8 --bs=128k --time_based --runtime=120"
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out,
                                    fio_user_data=fio_cmd)[0] == True
        
        assert pos.target_utils.device_hot_remove(device_list=[random.choice(data_disk_list)])
        assert pos.target_utils.array_rebuild_wait(array_name=array_name)

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)



@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives", 
                         [("RAID5", 3), ("RAID10", 2), ("RAID10", 4)])
def test_wt_array_rebuild_during_BlockIO(raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_rebuild_after_BlockIO ================== "
    )
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}")
 
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        spare_disk_list = [system_disks.pop()]

        array_name = "array1"
        assert pos.cli.create_array(write_buffer="uram0", data=data_disk_list,
                                    spare=spare_disk_list, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert pos.cli.create_volume("pos_vol1", array_name=array_name, size="1gb")[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                            volume_list=pos.cli.vols, nqn_list=ss_list) == True

        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, 
                            pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=8 --bs=128k --time_based --runtime=300"
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out,
                                    fio_user_data=fio_cmd, run_async=True)[0] == True
        
        time.sleep(120)    # Run IO for atleast 2 minutes before Hot Remove
        assert pos.target_utils.device_hot_remove(device_list=[random.choice(data_disk_list)])
        assert pos.target_utils.array_rebuild_wait(array_name=array_name)

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
