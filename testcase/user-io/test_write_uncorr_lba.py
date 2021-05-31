import logger, pytest

logger= logger.get_logger(__name__)

def test_pos_write_uncorr_lba(user_io):
    try:
      dev_list = user_io["client_setup"].device_list 
      fio_cmd = "fio --name=test_1 --ioengine=libaio --iodepth=256 --rw=write --size=100gb --bs=4kb  --numjobs=8"
      user_io["client_setup"].fio_generic_runner(devices  = dev_list, fio_data = fio_cmd)
      if user_io["client_setup"].status['ret_code'] is "fail":
         raise Exception(user_io["client_setup"].status['message'])

      user_io["target_setup"].list_vol(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
      vol_list = user_io["target_setup"].vols

      user_io["target_setup"].read_vsamap_entry(vol_name = vol_list[0], rba = 0, array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception(user_io["target_setup"].status['message'])
      vsid = user_io["target_setup"].read_vsamap_out['vsid']

      user_io["target_setup"].read_stripemap_entry(vsid = vsid, array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
      ls_id = user_io["target_setup"].stripemap_entry_out['lsid']

      user_io["target_setup"].translate_device_lba(logical_stripe_id = ls_id, logical_offset = 0, array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
      dev_name = user_io["target_setup"].dev_lba_out['device name ']
      lba = user_io["target_setup"].dev_lba_out['lba ']

      user_io["target_setup"].write_uncorrectable_lba(device_name = dev_name, lba = lba)
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].read_raw(dev = dev_name, lba = lba, count = 10)
      if user_io["target_setup"].status['ret_code'] is "pass":
         raise Exception (user_io["target_setup"].status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
