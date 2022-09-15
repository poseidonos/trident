import pytest
from pos import POS
import logger
logger = logger.get_logger(__name__)

def gc_array_io(pos):
    try:
        array_name="POSARRAY1"
        assert pos.cli.list_device()[0] == True
        system_disks = pos.cli.system_disks
        if len(system_disks) < (3):
            pytest.skip(
                f"Insufficient disk count {system_disks}. "
            )
        data_disk_list = [system_disks.pop(0) for i in range(3)]
        #spare_disk_list = [system_disks.pop()]

        assert (
            pos.cli.create_array(
                write_buffer="uram0",
                data=data_disk_list,
                spare=None,
                raid_type="RAID5",
                array_name=array_name,
            )[0]
            == True
        )
        assert pos.cli.mount_array(array_name=array_name, write_back=True)[0] == True
        assert pos.cli.create_volume(array_name=array_name, size="2000gb", volumename="vol")[0]== True
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.list_volume(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if "subsystem1" in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn=ss_list[0]
            )
            == True
        )

        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=30",
            )[0]
            == True
        )
        return True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.regression
@pytest.mark.parametrize("bs", [1, 3, 4, 5, 32, 33, 1024, 1023, 1203, 512, 513] )
def test_gc_diff_bk_size(array_fixture,bs):
    logger.info(
        " ==================== Test : test_gc_diff_bk_size ================== "
    )
    try:
        pos = array_fixture
        assert gc_array_io(pos) == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs={}k --time_based --runtime=10".format(bs)
            )[0]
            == True
        )
        assert pos.cli.wbt_do_gc()[0] == True
        assert pos.cli.wbt_get_gc_status()[0] == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
