import pytest
import logger

logger = logger.get_logger(__name__)

def test_verify_new_volume_uuid(volume_fixture):
    '''
        the purpose of the test is to verify uuid of an volume
        delete exiting volume and create new volume with same name 
    '''
    try:
        logger.info(
            f" ============== Test : start of test_verify_new_volume_uuid  ============="
        )
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        #creating volume
        assert pos.cli.volume_create(array_name=array_name,volumename="vol1",size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name, vol_name="vol1")[0] == True
        #verifying uuid of an volume is not equal to zero
        assert pos.cli.volume_data[array_name]["vol1"]["uuid"] != 0
        volume_uuid1 = pos.cli.volume_data[array_name]["vol1"]["uuid"]
        logger.info(f" Volume unique id : ", volume_uuid1)
        logger.info(volume_uuid1)
        #deleting the volume
        assert pos.cli.volume_unmount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_delete(array_name=array_name,volumename="vol1")[0] ==True
        assert pos.cli.volume_info(array_name=array_name, vol_name="vol1")[0] == False
        #creating volume with same name
        assert pos.cli.volume_create(array_name=array_name,volumename="vol1",size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name, vol_name="vol1")[0] == True
        #verifying uuid of an volume is not equal to zero
        assert pos.cli.volume_data[array_name]["vol1"]["uuid"] != 0
        volume_uuid2 = pos.cli.volume_data[array_name]["vol1"]["uuid"]
        logger.info(volume_uuid2)
        #verifying old and new uuid of volume's should not match
        assert volume_uuid1 != volume_uuid2
        logger.info(
            f" ============== Test : end of test_verify_new_volume_uuid  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)




def test_unmount_mount_volume_verify_uuid(volume_fixture):
    '''
        the purpose of the test is to verify uuid of an volume
        unmount exiting volume and mount back volume
    '''
    try:
        logger.info(
            f" ============== Test : start of test_unmount_mount_volume_verify_uuid  ============="
        )
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        #creating volume
        assert pos.cli.volume_create(array_name=array_name,volumename="vol1",size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name, vol_name="vol1")[0] == True
        #verifying uuid of an volume is not equal to zero
        assert pos.cli.volume_data[array_name]["vol1"]["uuid"] != 0
        volume_uuid1 = pos.cli.volume_data[array_name]["vol1"]["uuid"]
        logger.info(f" Volume unique id : ", volume_uuid1)
        logger.info(volume_uuid1)
        #unmounting the volume
        assert pos.cli.volume_unmount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name, vol_name="vol1")[0] == True
        #mounting back the volume
        assert pos.cli.volume_mount(array_name=array_name,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name, vol_name="vol1")[0] == True
        #verifying uuid of an volume is not equal to zero
        assert pos.cli.volume_data[array_name]["vol1"]["uuid"] != 0
        volume_uuid2 = pos.cli.volume_data[array_name]["vol1"]["uuid"]
        logger.info(volume_uuid2)
        #verifying old and new uuid of volume should match
        assert volume_uuid1 == volume_uuid2
        logger.info(
            f" ============== Test : end of test_unmount_mount_volume_verify_uuid  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)