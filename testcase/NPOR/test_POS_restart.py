import pytest, logger, os, json
logger = logger.get_logger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
with open("{}/../config_files/topology.json".format(dir_path)) as f:
    config_dict = json.load(f)

@pytest.mark.parametrize("io", [True, False])
def test_pos_npor_with_with_out_io(user_io, io):
    try:
      user_io["target_setup"].list_vol(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
      vol_list_bfr = user_io["target_setup"].vols

      if io:
         dev_list = user_io["client_setup"].device_list
         fio_cmd = "fio --name=S_W --runtime=50 --ioengine=libaio --iodepth=16 --rw=write --size=20g --bs=1m "
         user_io["client_setup"].fio_generic_runner(devices  = dev_list, fio_data = fio_cmd)
         if user_io["client_setup"].status['ret_code'] is "fail":
            raise Exception (user_io["client_setup"].status['message'])

      user_io["client_setup"].nvme_disconnect()
      if user_io["client_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["client_setup"].status['message'])

      user_io["target_setup"].stop()
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].start_pos_os()
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].create_Nvmf_SS()
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].create_malloc_device()
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception(target_setup.status['message'])

      user_io["target_setup"].scan_devs()
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].list_devs()
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].list_arrays()
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])
      array_name = list(user_io["target_setup"].list_arr_out.keys())[0]

      user_io["target_setup"].mount_array(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].list_vol(array_name = array_name)
      if user_io["target_setup"].status['ret_code'] is "fail":
         raise Exception (user_io["target_setup"].status['message'])

      if len(user_io["target_setup"].vols) == len(vol_list_bfr):
         logger.info("vol count matches after & before npor") 
      else:
         raise Exception ("volume count differs after NPOR")

      for vol in user_io["target_setup"].vols:
          user_io["target_setup"].mount_vol(volname = vol, array_name = "POSARRAY1")
          if user_io["target_setup"].status['ret_code'] is "fail":
             raise Exception (user_io["target_setup"].status['message'])

      if io:
         user_io["target_setup"].create_transport()
         if user_io["target_setup"].status['ret_code'] is "fail":
            raise Exception (user_io["target_setup"].status['message'])

         user_io["target_setup"].add_nvmf_listner(mellanox_interface = config_dict['login']['tar_mlnx_ip'])
         if user_io["target_setup"].status['ret_code'] is "fail":
            raise Exception (user_io["target_setup"].status['message'])

         user_io["client_setup"].nvme_connect(user_io["target_setup"].nqn_name, config_dict['login']['tar_mlnx_ip'])
         if user_io["client_setup"].status['ret_code'] is "fail":
            raise Exception (user_io["client_setup"].status['message'])

         user_io["client_setup"].list_nvme()
         if user_io["client_setup"].status['ret_code'] is "fail":
            raise Exception (user_io["client_setup"].status['message'])
         dev_list = user_io["client_setup"].device_list

         fio_cmd = "fio --name=S_W --runtime=50 --ioengine=libaio --iodepth=16 --rw=read --size=20g --bs=1m "
         user_io["client_setup"].fio_generic_runner(devices  = dev_list, fio_data = fio_cmd)
         if user_io["client_setup"].status['ret_code'] is "fail":
            raise Exception (user_io["client_setup"].status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
