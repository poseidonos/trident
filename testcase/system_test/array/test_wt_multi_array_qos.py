import pytest
from common_libs import *
import logger
logger = logger.get_logger(__name__)

@pytest.mark.regression


def multi_io(pos, IO):
        assert pos.client.nvme_list() == True
        if IO == "File":
            assert pos.client.create_File_system(device_list =  pos.client.nvme_list_out) == True
            assert pos.client.mount_FS(device_list = pos.client.nvme_list_out)[0] == True
            
            pos.client.fio_generic_runner( list(pos.client.mount_point.values()), IO_mode=False) 
             
            assert pos.client.unmount_FS(list(pos.client.mount_point.values())) == True
            assert pos.client.delete_FS(list(pos.client.mount_point.values())) == True

        else:
           assert pos.client.fio_generic_runner(
                pos.client.nvme_list_out
                              
            )[0] == True
           
@pytest.mark.parametrize("IO", ["File", "block"])
def test_wt_multi_array_qos(array_fixture, IO):

    logger.info(
        " ==================== Test : test_wt_multi_array_qos ================== "
    )
    try:
        pos = array_fixture
        pos.data_dict['volume']['pos_volumes'][0]['num_vol'] = 1
        pos.data_dict['volume']['pos_volumes'][1]['num_vol'] = 1
        assert pos.target_utils.bringupArray(data_dict = pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict = pos.data_dict) == True
        run_io(pos)
        multi_io(pos, IO)
        

        logger.info(
            " ============================= Test ENDs ======================================"
        )

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
