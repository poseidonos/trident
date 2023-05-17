import pytest
import time
import logger

logger = logger.get_logger(__name__)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("no-raid", 1), ("RAID0", 2), ("RAID10", 4)]
)
def test_wt_array_nvme_flush(array_fixture, raid_type, nr_data_drives):
    logger.info(
        " ==================== Test : test_wt_array_nvme_flush ================== "
    )
    try:
        pos = array_fixture
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
                volume_list=pos.cli.vols, nqn_list=ss_list[0]) == True
        
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for ss in subsys_list:
            assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=300",
        assert pos.client.fio_generic_runner(dev_list,
                    fio_user_data=fio_cmd, run_async=True)[0] == True

        assert pos.client.nvme_flush(dev_list) == True
        
        logger.info("Wait for 5 minutes till IO completes")
        time.sleep(300)
        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
