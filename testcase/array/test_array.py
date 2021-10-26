import logger, pytest

logger = logger.get_logger(__name__)


def test_create_check(array_management):
    pass


def test_array_rebuild(mount_array):
    try:
        array_info = mount_array.cli.get_array_info()
        data_drives = array_info[4]
        assert (
            mount_array.target_utils.device_hot_remove(device_list=[data_drives[0]])
            == True
        )
        array_info = mount_array.cli.get_array_info()
        array_state, array_situation = array_info[2], array_info[3]
        if array_state == "BUSY" and array_situation == "REBUILDING":
            logger.info("Array is in rebuilding state")
        else:
            raise Exception("Array is not in rebuilding state")
        mount_array.target_utils.check_rebuild_status()
        assert mount_array.cli.unmount_array() == True
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))
        assert 0


def test_unmount_pos_array(mount_array):
    try:
        assert mount_array.cli.unmount_array() == True
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))
        assert 0


def test_delete_array(array_management):
    try:
        assert array_management.cli.delete_array() == True
    except Exception as e:
        logger.error("testcase failed due to {}".format(e))
        assert 0


def test_create_array_2_data_disks(scan_dev):
    try:
        assert scan_dev.cli.create_array(data="unvme-ns-0,unvme-ns-1") == False
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))


def test_create_array_with_out_spare(scan_dev):
    try:
        assert scan_dev.cli.create_array(spare=None) == True
    except Exception as e:
        logger.error("Testcase failed due to {}".format(e))
        assert 0
