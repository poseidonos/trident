import logger
import pytest

logger= logger.get_logger(__name__)

@pytest.mark.parametrize("io", ["file", "block"])
def test_rebuild_io(user_io, io):
    try:
      flag = False  
      devs = user_io["target_setup"].NVMe_devices
      dev_list = user_io["client_setup"].device_list
      if io == "block":
         fio_cmd = "fio --name=S_W --runtime=180 --ioengine=libaio --iodepth=16 --rw=randwrite --size=1g --bs=4kb"  
         user_io["client_setup"].fio_generic_runner(devices  = dev_list, fio_data = fio_cmd)
         if user_io["client_setup"].status['ret_code'] is "fail":
            raise Exception(user_io["client_setup"].status['message'])

      if io == "file":
         user_io["client_setup"].create_FS(dev_list = dev_list, format_type = "xfs")
         if user_io["client_setup"].status['ret_code'] is "fail":
            raise Exception (user_io["client_setup"].status['message'])

         user_io["client_setup"].mount_FS(dev_list = dev_list)
         if user_io["client_setup"].status['ret_code'] is "fail":
            raise Exception(user_io["client_setup"].status['message'])
         flag = True
         dev_fs_list = user_io["client_setup"].device_FS_list

         fio_cmd = "fio --name=S_W  --ioengine=libaio  --iodepth=16 --rw=write --size=1g --bs=8k \
                   --verify=pattern --do_verify=0 --verify_pattern=0xa66"
         user_io["client_setup"].fio_generic_runner(devices  = dev_fs_list, fio_data = fio_cmd, io_mode = False)
         if user_io["client_setup"].status['ret_code'] is "fail":
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list) 
            raise Exception (user_io["client_setup"].status['message'])

      user_io["target_setup"].list_array_devices(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list) 
         raise Exception (user_io["target_setup"].status['message'])
      logger.info(user_io["target_setup"].data_disks)

      user_io["target_setup"].detach_dev(device_name = [user_io["target_setup"].data_disks[0]])
      if user_io["target_setup"].status['ret_code'] is "fail":
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
         raise Exception (user_io["target_setup"].status['message'])

      user_io["target_setup"].get_array_info(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         user_io["target_setup"].pci_rescan()
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
         raise Exception (user_io["target_setup"].status['message'])   
      logger.info(user_io["target_setup"].array_state)

      if user_io["target_setup"].array_state == "REBUILDING":
         logger.info("array state is in rebuilding state")
         user_io["target_setup"].pci_rescan()
      else:
         user_io["target_setup"].pci_rescan()
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
         raise Exception ("array state is not in rebuilding state")

      user_io["target_setup"].check_rebuild_status(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
         raise Exception (user_io["target_setup"].status['message'])   
    
      if io == "block":
         fio_cmd = "fio --name=S_W --runtime=180 --ioengine=libaio --iodepth=16 --rw=read --size=1g --bs=4kb"
         user_io["client_setup"].fio_generic_runner(devices  = dev_list, fio_data = fio_cmd)
         if user_io["client_setup"].status['ret_code'] is "fail":
            if io == "file" and flag == True:
               user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
            raise Exception (user_io["client_setup"].status['message'])

      if io == "file":
         fio_cmd = "fio --name=S_W  --ioengine=libaio  --iodepth=16 --rw=read --size=1g --bs=8k \
                   --verify=pattern --do_verify=0 --verify_pattern=0xa66"
         user_io["client_setup"].fio_generic_runner(devices  = dev_fs_list, fio_data = fio_cmd, io_mode = False)
         if user_io["client_setup"].status['ret_code'] is "fail":
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
            raise Exception(user_io["client_setup"].status['message'])

      user_io["target_setup"].list_devs()
      if user_io["target_setup"].status['ret_code'] is "fail":
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
         raise Exception (user_io["target_setup"].status['message'])
      devs_1 = user_io["target_setup"].NVMe_devices

      user_io["target_setup"].list_array_devices(array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
         raise Exception(user_io["target_setup"].status['message'])

      spare_dev = [dev for dev in devs_1 if dev not in devs if dev not in user_io["target_setup"].spare_disks]

      user_io["target_setup"].add_spare_drive(device_name = spare_dev[0], array_name = "POSARRAY1")
      if user_io["target_setup"].status['ret_code'] is "fail":
         if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
         raise Exception(user_io["target_setup"].status['message'])
      if io == "file" and flag == True:
         user_io["client_setup"].unmount_FS(unmount_dir = dev_fs_list)
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
