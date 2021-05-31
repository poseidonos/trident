import logger, pytest

logger = logger.get_logger(__name__)

@pytest.fixture(scope = "module")

def create_array(array_fixture):
    logger.info(array_fixture.NVMe_devices)
    array_fixture.create_array(num_ds = len(array_fixture.NVMe_devices)-1, spare_count = 1, array_name = "POSARRAY1")
    if array_fixture.status['ret_code'] is "fail":
       logger.error(array_fixture.status['message'])
       pytest.skip()
    else:
       logger.info(array_fixture.status['message'])


def test_array_rebuild(array_fixture,create_array):
    try:
      logger.info(array_fixture.NVMe_devices)
      array_fixture.mount_array(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])

      array_fixture.list_array_devices(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])
      logger.info(array_fixture.data_disks)

      array_fixture.detach_dev(device_name = [array_fixture.data_disks[0]])
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])

      array_fixture.get_array_info(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         array_fixture.pci_rescan()
         raise Exception (array_fixture.status['message'])

      if array_fixture.array_state == "REBUILDING":
         logger.info("array state is in rebuilding state")
      else:
         array_fixture.pci_rescan() 
         raise Exception ("array state is not in rebuilding state")

      array_fixture.check_rebuild_status(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         array_fixture.pci_rescan() 
         raise Exception (array_fixture.status['message'])
      array_fixture.pci_rescan()
      array_fixture.unmount_array(array_name = "POSARRAY1")
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        array_fixture.pci_rescan()
        array_fixture.unmount_array(array_name = "POSARRAY1")
        assert 0

def test_unmount_pos_array(array_fixture,create_array):
    try:
      array_fixture.mount_array(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])

      array_fixture.unmount_array(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_del_array(array_fixture,create_array):
    try:
      array_fixture.delete_array(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_create_array_2_data_disks(array_fixture):
    try:
      array_fixture.list_devs()
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])
      logger.info(array_fixture.NVMe_devices)

      array_fixture.create_array(num_ds = 2, spare_count = 0,array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "pass":
         raise Exception (array_fixture.status['message'])

    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_create_array_with_out_spare(array_fixture):
    try:
      array_fixture.list_devs()
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])
      logger.info(array_fixture.NVMe_devices)

      array_fixture.create_array(num_ds = len(array_fixture.NVMe_devices), spare_count = 0,array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])

      array_fixture.delete_array(array_name = "POSARRAY1")
      if array_fixture.status['ret_code'] is "fail":
         raise Exception (array_fixture.status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
