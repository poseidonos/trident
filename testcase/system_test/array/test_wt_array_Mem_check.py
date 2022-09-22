import pytest

import logger

logger = logger.get_logger(__name__)

array_list = [
    ("no-raid", 1, "Block"),
    ("RAID0", 2, "Block"),
    ("RAID10", 4, "Block"),
    ("RAID10", 2, "Block"),
    ("no-raid", 1, "File"),
    ("RAID0", 2, "File"),
    ("RAID10", 4, "File"),
    ("RAID10", 2, "File"),
]


@pytest.mark.regression
@pytest.mark.parametrize("raid_type, nr_data_drives, IO", array_list)
def test_wt_array_Mem_check(
    setup_cleanup_array_function, raid_type, nr_data_drives, IO
):
    logger.info(
        " ==================== Test : test_wt_array_Mem_check ================== "
    )
    try:
        pos = setup_cleanup_array_function
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True

        assert pos.cli.scan_device()[0] == True
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        array_name = "posarray1"
        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type=raid_type,
                array_name=array_name,
            )[0]
            == True
        )

        assert pos.cli.mount_array(array_name=array_name, write_back=False)[0] == True
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
        pos.client.check_system_memory()

        if IO == "File":
            dev = [pos.client.nvme_list_out[0]]

            assert pos.client.create_File_system(dev, fs_format="xfs")
            status, mount_point = pos.client.mount_FS(dev)
            assert status == True

            fio_cmd = "fio --name=Rand_RW  --runtime=300 --ramp_time=60  --ioengine=sync  --iodepth=32 --rw=write --size=1000g bs=32kb --direct=1 --verify=md5"
            assert (
                pos.client.fio_generic_runner(
                    mount_point, fio_user_data=fio_cmd, IO_mode=False, run_async=True
                )[0]
                == True
            )
            assert status == True
            assert pos.client.unmount_FS(mount_point) == True
            assert pos.client.delete_FS(mount_point) == True

        else:

            assert (
                pos.client.fio_generic_runner(
                    pos.client.nvme_list_out,
                    fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=300",
                    run_async=True,
                )[0]
                == True
            )
        pos.client.check_system_memory()

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        if IO == "File":
            assert pos.client.unmount_FS(mount_point) == True
            assert pos.client.delete_FS(mount_point) == True
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
