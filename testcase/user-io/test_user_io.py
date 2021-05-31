import logger, pytest

logger= logger.get_logger(__name__)

@pytest.mark.parametrize("io_engine", ["posixaio", "sync", "libaio"])
def test_run_block_io(user_io,io_engine):
    try:
      dev_list = user_io["client_setup"].device_list
      fio_cmd = "fio --name=S_W --runtime=5 --ioengine={} --iodepth=16 --rw=write --size=1g --bs=1m ".format(io_engine)
      user_io["client_setup"].fio_generic_runner(devices  = dev_list, fio_data = fio_cmd)
      if user_io["client_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["client_setup"].status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

@pytest.mark.parametrize("fs_type", ["ext3","ext4","xfs"])
@pytest.mark.parametrize("io_engine", ["posixaio", "sync", "libaio"])
def test_run_file_io(user_io,fs_type,io_engine):
    try:
      dev_list = user_io["client_setup"].device_list
      user_io["client_setup"].create_FS(dev_list = dev_list, format_type=fs_type)
      if user_io["client_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["client_setup"].status['message'])

      user_io["client_setup"].mount_FS(dev_list = dev_list)
      if user_io["client_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["client_setup"].status['message'])
      dev_fs_list = user_io["client_setup"].device_FS_list
       
      fio_cmd = "fio --name=S_W --runtime=5 --ioengine={} --iodepth=16 --rw=write --size=1g --bs=1m ".format(io_engine)
      user_io["client_setup"].fio_generic_runner(devices  = dev_fs_list, fio_data = fio_cmd, io_mode = False)
      if user_io["client_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["client_setup"].status['message'])
      user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
        assert 0
