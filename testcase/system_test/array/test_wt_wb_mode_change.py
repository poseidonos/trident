import pytest
import logger

logger = logger.get_logger(__name__)

def por_array_io(pos, raid_type, nr_data_drives):
    try:
        array1 = pos.data_dict["array"]["pos_array"][0]
        array_name = array1["array_name"]
        buffer_dev = array1["uram"]
        system_disks = pos.cli.system_disks
        data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]
        assert pos.cli.array_create(array_name=array_name,
                                    write_buffer=buffer_dev,
                                    data=data_disk_list,
                                    spare=[], raid_type=raid_type,
                                    )[0] == True
        assert pos.cli.array_mount(array_name=array_name, 
                                   write_back=True)[0] == True
        assert pos.cli.volume_create(array_name=array_name,
                           size="2000gb", volumename="vol")[0] == True

        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]

        assert pos.target_utils.mount_volume_multiple(array_name=array_name,
                           volume_list=pos.cli.vols, nqn=ss_list[0]) == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=300"
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out,
                                             fio_user_data=fio_cmd)[0] == True
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("RAID0", 2), ("RAID5", 3), ("RAID10", 2)]
)
def test_wt_array_single_vol_npor(array_fixture, raid_type, nr_data_drives):
    try:
        pos = array_fixture
        assert por_array_io(pos, raid_type, nr_data_drives) == True
        assert pos.target_utils.npor() == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize(
    "raid_type, nr_data_drives", [("RAID5", 3), ("RAID10", 2), ("RAID0", 2)]
)
def test_wt_array_single_vol_spor(array_fixture, raid_type, nr_data_drives):
    try:
        pos = array_fixture
        assert por_array_io(pos, raid_type, nr_data_drives) == True
        assert pos.target_utils.spor() == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
