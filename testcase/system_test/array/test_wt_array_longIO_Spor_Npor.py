import pytest

from pos import POS
import logger
import random
import time


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


    assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)
@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives,por",
                         [ ("no-raid", 1,Npor), ("RAID0", 2,Npor), ("RAID10", 4,Npor),("no-raid", 1,Spor), ("RAID0", 2,Spor), ("RAID10", 4,Spor)])
def test_wb_wt_array_long_fileIO_Npor_Spor(raid_type, nr_data_drives,por):
    """The purpose of this test case is to Create one array in Write Through mode. Create and mount 1 volume and run file IO from initiator for 12 hours"""
    logger.info(
        " ==================== Test : test_wb_wt_array_long_fileIO_Npor_Spor ================== "
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
        array_name = "posarray1"
        assert pos.cli.create_array(write_buffer="uram0", data=data_disk_list,
                                    spare=None, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        assert pos.cli.mount_array(array_name=array_name)[0] == True
        assert pos.cli.create_volume("pos_vol_1", array_name=array_name, size="2000gb")[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem1" in ss]
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                            volume_list=pos.cli.vols, nqn_list=ss_list) == True

        assert pos.client.nvme_connect(ss_list[0],
                                       pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True
        dev = [pos.client.nvme_list_out[0]]

        assert pos.client.create_File_system(dev, fs_format="xfs")
        status, mount_point = pos.client.mount_FS(dev)
        assert status == True

        fio_cmd = "fio --name=Rand_RW  --runtime=43 --ramp_time=60  --ioengine=sync  --iodepth=32 --rw=write --size=1000g bs=32kb --direct=1 --verify=md5"

        status , io_pro = pos.client.fio_generic_runner(mount_point, fio_user_data=fio_cmd, IO_mode=False, run_async=True)
        assert status == True
        assert pos.client.unmount_FS(mount_point) == True
        assert pos.client.delete_FS(mount_point) == True

        if por == "Npor":
            assert pos.target_utils.Npor() == True
        else:
            assert pos.target_utils.Spor() == True
        # unmount and delete array and volume


        assert pos.cli.list_volume(array_name=array_name)[0] == True
        for volume in pos.cli.vols:
            pos.cli.unmount_volume(volumename=volume, array_name=array_name)
            pos.cli.delete_volume(volumename=volume, array_name=array_name)
        assert pos.cli.info_array(array_name=array_name)[0] == True
        assert pos.cli.unmount_array(array_name=array_name)[0] == True
        assert pos.cli.delete_array(array_name=array_name)[0] == True


        array_name = "posarray2"
        assert pos.cli.create_array(write_buffer="uram0", data=data_disk_list,
                                    spare=None, raid_type=raid_type,
                                    array_name=array_name)[0] == True

        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True
        assert pos.cli.create_volume("pos_vol_1New", array_name=array_name, size="2000gb")[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem2" in ss]
        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                                                      volume_list=pos.cli.vols, nqn_list=ss_list) == True

        assert pos.client.nvme_connect(ss_list[0],
                                           pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True
        dev = [pos.client.nvme_list_out[0]]
        assert pos.client.create_File_system(dev, fs_format="xfs") == True
        status, mount_point_new = pos.client.mount_FS(dev)
        assert status == True

        fio_cmd = "fio --name=Rand_RW  --runtime=43 --ramp_time=60  --ioengine=sync  --iodepth=32 --rw=write --size=10g bs=32kb --direct=1 --verify=md5"
        status , io_pro = pos.client.fio_generic_runner(mount_point_new, fio_user_data=fio_cmd, IO_mode=False, run_async=True)
        assert status == True
        assert pos.client.unmount_FS(mount_point_new) == True
        assert pos.client.delete_FS(mount_point_new) == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

