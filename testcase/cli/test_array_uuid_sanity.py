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