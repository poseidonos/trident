import logger
import pytest

logger = logger.get_logger(__name__)


@pytest.mark.parametrize("io", [True, False])
def test_pos_wbt_flush(user_io, io):
    try:
        dev_list = user_io["client_setup"].device_list
        if io:
            fio_cmd = "fio --name=S_W --runtime=180 --ioengine=libaio --iodepth=16 --rw=randwrite --size=1g --bs=4kb"
            user_io["client_setup"].fio_generic_runner(
                devices=dev_list, fio_data=fio_cmd
            )
            user_io["target_setup"].cli.flush(array_name="POS_ARRAY1")
        else:
            user_io["target_setup"].cli.flush(array_name="POS_ARRAY1")
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0


@pytest.mark.parametrize("bs", [1, 4, 32, 1024])
@pytest.mark.parametrize("io_depth", [16, 32])
def test_do_flush_diff_bs(user_io, bs, io_depth):
    try:
        dev_list = user_io["client_setup"].device_list
        fio_cmd = "fio --name=S_W --runtime=180 --ioengine=libaio --iodepth={} --rw=write --size=1g --bs={}k".format(
            io_depth, bs
        )
        user_io["client_setup"].fio_generic_runner(devices=dev_list, fio_data=fio_cmd)
        user_io["client_setup"].nvme_flush(dev_list=dev_list)
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
