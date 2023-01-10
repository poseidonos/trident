import logger
import pytest
import common_libs as setup
logger = logger.get_logger(__name__)

@pytest.mark.parametrize("io_type",["write","read","randwrite","randread"])
def test_verify_data_corruption_seq_write(array_fixture,io_type):

    pos = array_fixture

    assert setup.multi_array_data_setup(data_dict = pos.data_dict,num_array = 2,
                                        raid_types = ("RAID6","RAID6"),
                                        num_data_disks=(4,4),
                                        num_spare_disk=(0,0),
                                        auto_create=(False,False),
                                        array_mount=("WT","WT")) == True
    assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
    assert pos.cli.array_list()[0] == True
    assert pos.target_utils.get_subsystems_list() == True
    assert setup.volume_create_and_mount_multiple(pos=pos,
                                                  num_volumes=1,
                                                  array_list=pos.cli.array_dict.keys(),
                                                  subs_list=pos.target_utils.ss_temp_list) == True

    assert setup.nvme_connect(pos=pos)[0] == True

    fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw={} --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime={} --verify=md5"
    assert pos.client.fio_generic_runner(devices=setup.nvme_connect(pos=pos)[1],
                                         fio_user_data=fio_cmd.format(io_type, "435200"))[0] == True
    if "write" in io_type:
        io_type.replace("write","read")
    else:
        io_type.replace("read","write")

    logger.info("Checking for data corruption........")
    assert pos.client.fio_generic_runner(devices=setup.nvme_connect(pos=pos)[1],
                                         fio_user_data=fio_cmd.format(io_type, "18000"))[0] == True, "Data corruption detected!"