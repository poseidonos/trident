import pytest
import logger

logger = logger.get_logger(__name__)

def test_volume_uuid_of_two_array(volume_fixture):
    '''
        the purpose of the test is to verify uuid of an volume
        creating volume with same name on two arrays 
    '''
    try:
        logger.info(
            f" ============== Test : start of test_volume_uuid_of_two_array  ============="
        )
        pos = volume_fixture
        assert pos.cli.array_list()[0] == True
        array_name1 = list(pos.cli.array_dict.keys())[0]
        #create vol1 on array1
        assert pos.cli.volume_create(array_name=array_name1,volumename="vol1",size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array_name1,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name1, vol_name="vol1")[0] == True
        #verifying uuid of an volume is not equal to zero
        assert pos.cli.volume_data[array_name1]["vol1"]["uuid"] != 0
        volume_uuid1 = pos.cli.volume_data[array_name1]["vol1"]["uuid"]
        logger.info(f" Volume unique id : ", volume_uuid1)
        logger.info(volume_uuid1)
        assert pos.cli.array_list()[0] == True
        array_name2 = list(pos.cli.array_dict.keys())[1]
        #create vol1 on array2
        assert pos.cli.volume_create(array_name=array_name2,volumename="vol1",size='1gb')[0] == True
        assert pos.cli.volume_mount(array_name=array_name2,volumename="vol1")[0] == True
        assert pos.cli.volume_info(array_name=array_name2, vol_name="vol1")[0] == True
        #verifying uuid of an volume is not equal to zero
        assert pos.cli.volume_data[array_name2]["vol1"]["uuid"] != 0
        volume_uuid2 = pos.cli.volume_data[array_name2]["vol1"]["uuid"]
        logger.info(f" Volume unique id : ", volume_uuid2)
        logger.info(volume_uuid2)
        #verifying uuid of array1 vol1 and array2 vol1 should not match
        assert volume_uuid1 != volume_uuid2
        logger.info(
            f" ============== Test : end of test_volume_uuid_of_two_array  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)