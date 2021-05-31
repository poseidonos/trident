import logger 
import pytest

logger= logger.get_logger(__name__)

@pytest.mark.parametrize("bs", [1,3,4,5,32,33,123,1024])
def test_do_gc_diff_bs(user_io,bs):
    try:
      dev_list = user_io["client_setup"].device_list
      fio_cmd = "fio --name=S_W --runtime=180 --time_based --ioengine=libaio --iodepth=16 --rw=randwrite --size=1g --bs={}k".format(bs)
      user_io["client_setup"].fio_generic_runner(devices  = dev_list, fio_data = fio_cmd)
      if user_io["client_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["client_setup"].status['message'])

      user_io["target_setup"].do_gc(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_get_gc_status(user_io):
    try:
      user_io["target_setup"].get_gc_status(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_fetch_default_gc_values(user_io):
    try:
      user_io["target_setup"].get_gc_threshold(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_set_verify_gc_values(user_io):
    try:
      user_io["target_setup"].get_gc_status(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception(user_io["target_setup"].status['message'])
      logger.info(user_io["target_setup"].gc_status_out)

      free_seg = user_io["target_setup"].gc_status_out['gc']['segment']['free']

      user_io["target_setup"].set_gc_threshold(normal = free_seg, urgent = 20, array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception(user_io["target_setup"].status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
