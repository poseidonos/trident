import pytest
import logger

logger = logger.get_logger(__name__)

@pytest.mark.sanity
def test_verify_new_array_uuid(array_fixture):
    '''
        the purpose of the test is to verify uuid of an array
        delete exiting array and create new array with same name 
    '''
    try:
        logger.info(
            f" ============== Test : start of test_verify_new_array_uuid  ============="
        )
        pos = array_fixture
        #creating array
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.array_info(array_name=array_name)[0] == True
        assert pos.cli.array_info(array_name)[0] == True
        array_uuid1 = pos.cli.array_data[array_name]
        #verifying uuid of an array is not equal to zero
        assert pos.cli.array_data[array_name]["uniqueId"] != 0
        logger.info(f" Array unique id : ", array_uuid1["uniqueId"])
        logger.info(array_uuid1["uniqueId"])
        #deleting both arrays created
        array_name = "array1"
        assert pos.cli.array_unmount(array_name=array_name)[0] == True
        assert pos.cli.array_delete(array_name=array_name)[0] == True
        array_name = "array2"
        assert pos.cli.array_unmount(array_name=array_name)[0] == True
        assert pos.cli.array_delete(array_name=array_name)[0] == True
        #creating array
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.array_info(array_name=array_name)[0] == True
        assert pos.cli.array_info(array_name)[0] == True
        array_uuid2 = pos.cli.array_data[array_name]
        #verifying uuid of an array is not equal to zero
        assert pos.cli.array_data[array_name]["uniqueId"] != 0
        logger.info(f" Array unique id : ", array_uuid2["uniqueId"])
        logger.info(array_uuid2["uniqueId"])
        #verifying old and new array's uuid should not match
        assert array_uuid1 != array_uuid2
        logger.info(
            f" ============== Test : end of test_verify_new_array_uuid  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.sanity
def test_array_uuid(array_fixture):
    '''
        the purpose of the test is to list array uuid
    '''
    try:
        logger.info(
            f" ============== Test : start of test_array_uuid  ============="
        )
        pos = array_fixture
        #creating array
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.array_info(array_name=array_name)[0] == True
        assert pos.cli.array_info(array_name)[0] == True
        array_uuid = pos.cli.array_data[array_name]
        logger.info(f" Array unique id : ", array_uuid["uniqueId"])
        logger.info(array_uuid["uniqueId"])
        #verifying uuid of an array is not equal to zero
        assert pos.cli.array_data[array_name]["uniqueId"] != 0
        logger.info(
            f" ============== Test : end of test_array_uuid  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)



def test_multi_array_uuid(array_fixture):
    '''
        the purpose of the test is to verify uuid of multiple array
    '''
    try:
        logger.info(
            f" ============== Test : start of test_multi_array_uuid  ============="
        )
        pos = array_fixture
        #creating array
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.cli.array_list()[0] == True
        array1_name = list(pos.cli.array_dict.keys())[0]
        assert pos.cli.array_info(array_name=array1_name)[0] == True
        assert pos.cli.array_info(array1_name)[0] == True
        array1_uuid = pos.cli.array_data[array1_name]
        logger.info(f" Array unique id : ", array1_uuid["uniqueId"])
        logger.info(array1_uuid["uniqueId"])
        #verifying uuid of an array is not equal to zero
        assert pos.cli.array_data[array1_name]["uniqueId"] != 0
        array2_name = list(pos.cli.array_dict.keys())[1]
        assert pos.cli.array_info(array_name=array2_name)[0] == True
        assert pos.cli.array_info(array2_name)[0] == True
        array2_uuid = pos.cli.array_data[array2_name]
        logger.info(f" Array unique id : ", array1_uuid["uniqueId"])
        logger.info(array2_uuid["uniqueId"])
        #verifying uuid of an array is not equal to zero
        assert pos.cli.array_data[array2_name]["uniqueId"] != 0
        assert array1_uuid != array2_uuid
        logger.info(
            f" ============== Test : end of test_multi_array_uuid  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.sanity
def test_volume_uuid(volume_fixture):
    '''
        the purpose of the test is to list volume uuid
    '''
    try:
        logger.info(
            f" ============== Test : start of test_volume_uuid  ============="
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
        volume_uuid = pos.cli.volume_data[array_name]["vol1"]["uuid"]
        logger.info(f" Volume unique id : ", volume_uuid)
        logger.info(volume_uuid)
        logger.info(
            f" ============== Test : end of test_volume_uuid  ============="
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.sanity
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