import logger 
import random, pytest

logger= logger.get_logger(__name__)

@pytest.fixture(scope = "module")

def create_vol(vol_fixture):
    vol_fixture.create_mount_multiple(volname = "test",num_vols = 5, size = "100gb",array_name = "POSARRAY1")
    if vol_fixture.status['ret_code'] is "fail":
       logger.error(vol_fixture.status['message'])
       pytest.skip()
    else:
       logger.info(vol_fixture.status['message'])


def test_vol_create(vol_fixture):
    try:
      vol_fixture.get_pos_info_system()
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception ("pos is not running!")

      vol_fixture.get_array_info(array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception (vol_fixture.status['message'])
      array_size = vol_fixture.array_status
      remain_size = array_size["capacity"] - array_size["used"]
      reamin_size_gb = (round(remain_size/(1024 * 1024 * 1024)))
      vol_size_bytes = (reamin_size_gb - 1)* 1024 * 1024 * 1024

      vol_fixture.create_vol(size = int(array_size["capacity"]),array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception (vol_fixture.status['message'])

      vol_fixture.list_vol(array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception (vol_fixture.status['message'])
      logger.info(vol_fixture.vols)

      for vol in vol_fixture.vols:
          vol_fixture.delete_vol(volname = vol, array_name = "POSARRAY1")
          if vol_fixture.status['ret_code'] is "fail":
             raise Exception (vol_fixture.status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_vol_1ist(vol_fixture,create_vol):
    try:
      vol_fixture.list_vol(array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception (vol_fixture.status['message'])
      logger.info(vol_fixture.vols)
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_vol_mount_unmount_delete(vol_fixture,create_vol):
    try:
      vols = []
      vol_fixture.list_vol(array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception (vol_fixture.status['message'])
      logger.info(vol_fixture.vol_dict)

      for vol_data in vol_fixture.vol_dict:
          if vol_data['status'] == "Unmounted":
             vols.append(vol_data['name'])

      if len(vols) != 0:
         for vol in vols:
             vol_fixture.mount_vol(volname = vol, array_name = "POSARRAY1")
             if vol_fixture.status['ret_code'] is "fail":
                raise Exception (vol_fixture.status['message'])
            
      for vol in vol_fixture.vols:
          vol_fixture.unmount_vol(volname = vol, array_name = "POSARRAY1")
          if vol_fixture.status['ret_code'] is "fail":
             raise Exception (vol_fixture.status['message'])

          vol_fixture.delete_vol(volname = vol, array_name = "POSARRAY1")
          if vol_fixture.status['ret_code'] is "fail":
             raise Exception (vol_fixture.status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

@pytest.mark.parametrize("length", [[1,"pass"],[2,"fail"],[63,"fail"],[255, "fail"]])
def test_vol_create_diff_chars_length(vol_fixture,length):
    try:
      vol_name = "a"* length[0]

      vol_fixture.create_vol(volname = vol_name, array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is length[1]:
         raise Exception(vol_fixture.status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0

def test_create_max_vol(vol_fixture):
    try:
      vol_fixture.list_vol(array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception (vol_fixture.status['message'])
      logger.info(vol_fixture.vols)

      size = "1{}".format(random.choice(["mb","gb"]))
      vol_count = int(256 - len(vol_fixture.vols))
      vol_fixture.create_mount_multiple(volname = "test_vol", size = size, num_vols = vol_count, array_name = "POSARRAY1")
      if vol_fixture.status['ret_code'] is "fail":
         raise Exception(vol_fixture.status['message'])
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
