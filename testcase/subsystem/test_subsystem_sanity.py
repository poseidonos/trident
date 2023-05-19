import pytest
import logger
from pos import POS

logger = logger.get_logger(__name__)


@pytest.mark.sanity
def test_sanitySubsystem(array_fixture):
    try:
        pos = array_fixture
        assert pos.target_utils.get_subsystems_list() == True
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True
        
        assert pos.target_utils.get_subsystems_list() == True

    except Exception as e:
        logger.error(f"TC failed due to {e}")
        assert 0
