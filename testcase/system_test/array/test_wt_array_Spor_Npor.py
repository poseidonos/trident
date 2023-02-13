import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives,por",
    [
        ("no-raid", 1, "Npor"),
        ("RAID0", 2, "Npor"),
        ("RAID10", 4, "Npor"),
        ("RAID10", 2, "Npor"),
        ("no-raid", 1, "Spor"),
        ("RAID0", 2, "Spor"),
        ("RAID10", 4, "Spor"),
        ("RAID10", 2, "Spor"),
    ],
)
def test_wt_array_Npor_Spor_nobackup(
    array_fixture, raid_type, nr_data_drives, por
):

    logger.info(
        " ==================== Test : test_wt_array_Npor_Spor_nobackup ================== "
    )
    try:
        pos = array_fixture
        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (nr_data_drives + 1):
            pytest.skip(
                f"Insufficient disk count {system_disks}. Required minimum {nr_data_drives + 1}"
            )
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

        array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
        assert pos.cli.array_create(array_name=array_name,
                    write_buffer="uram0", data=data_disk_list,
                    spare=[], raid_type=raid_type)[0] == True

        assert pos.cli.array_mount(array_name=array_name,
                                   write_back=False)[0] == True
        assert pos.cli.volume_create("pos_vol_1", size="2000gb",
                                array_name=array_name)[0] == True
        
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        subsys_list = pos.target_utils.ss_temp_list
        ss_list = [ss for ss in subsys_list if array_name in ss]
        assert pos.target_utils.mount_volume_multiple(array_name, 
                    volume_list=pos.cli.vols, nqn=ss_list[0]) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=50",
            
        assert pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data=fio_cmd)[0] == True
        
        if por == "Npor":
            assert pos.target_utils.npor() == True
        else:
            assert pos.target_utils.spor(uram_backup=False) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
