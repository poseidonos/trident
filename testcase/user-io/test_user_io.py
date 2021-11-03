import logger, pytest

logger = logger.get_logger(__name__)


@pytest.mark.parametrize("io_engine", ["posixaio", "sync", "libaio"])
def test_run_block_io(user_io, io_engine):
    try:
        dev_list = user_io["client"].nvme_list()[1]

        fio_cmd = "fio --name=S_W --runtime=5 --ioengine={} --iodepth=16 --rw=write --size=1g --bs=1m ".format(
            io_engine
        )
        user_io["client"].fio_generic_runner(devices=dev_list, fio_user_data=fio_cmd)
    except Exception as e:
        logger.error("Test case failed with exception {}".format(e))
        assert 0
