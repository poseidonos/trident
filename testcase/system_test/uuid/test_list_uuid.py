import pytest
import logger

logger = logger.get_logger(__name__)

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