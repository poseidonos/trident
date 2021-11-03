import logger
import pytest

logger = logger.get_logger(__name__)


@pytest.mark.parametrize("bs", [1, 3, 4, 5, 32, 33, 123, 1024])
def test_do_gc_diff_bs(user_io, bs):
    try:
        dev_list = user_io["client"].nvme_list()[1]
        fio_cmd = "fio --name=S_W --runtime=180 --time_based --ioengine=libaio --iodepth=16 --rw=randwrite --size=1g --bs={}k".format(
            bs
        )
        assert (
            user_io["client"].fio_generic_runner(
                devices=dev_list, fio_user_data=fio_cmd
            )
            == True
        )
        assert user_io["target"].cli.do_gc(array_name="POS_ARRAY1") == True
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0


def test_get_gc_status(user_io):
    try:
        assert user_io["target"].cli.get_gc_status(array_name="POS_ARRAY1") == True
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0


def test_fetch_default_gc_values(user_io):
    try:
        assert user_io["target"].cli.get_gc_threshold(array_name="POS_ARRAY1") == True
    except Exception as e:
        logger.error("Test case failed with exception {}".format(e))
        assert 0


def test_set_verify_gc_values(user_io):
    try:
        assert user_io["target"].cli.get_gc_status(array_name="POS_ARRAY1") == True
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
