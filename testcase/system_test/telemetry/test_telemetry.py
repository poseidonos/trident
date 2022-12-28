from prometheus import Prometheus as prom
from common_libs import *
import logger
logger = logger.get_logger(__name__)

def test_verify_pos_metrics(array_fixture):
    pos = array_fixture
    try:
        assert pos.prometheus.set_telemetry_configs() == True
        assert pos.cli.list_device()[0] == True
        logger.info(pos.cli.system_disks)
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        assert pos.cli.list_array()[0] == True
        arrays = list(pos.cli.array_dict.keys())
        for array in arrays:
            assert pos.cli.info_array(array_name=array)[0] == True
            array_info = pos.cli.array_info[array]
            assert pos.prometheus.array_states[pos.prometheus.get_array_state(uniqueid=array_info['uniqueId'])] == array_info['situation']
            assert pos.prometheus.get_total_array_capacity(array_id=str(array_info['index'])) == str(array_info['size'])
            # assert pos.prometheus.get_used_array_capacity(array_id=str(array_info['index']) == str(array_info['used']))
            assert pos.cli.list_volume(array_name=array)[0] == True
            for vol in list(pos.cli.vols):
                assert pos.cli.info_volume(array_name=array,vol_name=vol)[0] == True
                assert pos.prometheus.get_volume_capacity_total(array_name=array,volume_name=vol) == str(pos.cli.volume_info[array][vol]['total_capacity']) ,"Total volume capacity does not match"
                assert pos.prometheus.get_volume_capacity_used(array_id=str(array_info['index']), volume_id=str(pos.cli.vol_dict[vol]['index'])) == str(pos.cli.vol_dict[vol]['total'] - pos.cli.volume_info[array][vol]['remain']),"Used volume capacity does not match"
                assert pos.prometheus.volume_states[pos.prometheus.get_volume_state(array_name=array,volume_name=vol)] == pos.cli.volume_info[array][vol]['status'].lower(),"Volume status does not match"
                logger.info(pos.prometheus.get_volume_state(array_name=array,volume_name=vol))
                logger.info(pos.prometheus.get_volume_capacity_total(array_name=array,volume_name=vol))
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_verify_volume_states(array_fixture):
    pos = array_fixture
    try:
        assert pos.prometheus.set_telemetry_configs() == True
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        arrays = list(pos.cli.array_dict.keys())
        for array in arrays:
            assert pos.cli.list_volume(array_name=array)[0] == True
            logger.info(pos.prometheus.get_volume_state(array_name=array,volume_name=vol))
            assert pos.cli.unmount_volume(array_name=array,volumename=vol)[0] == True
            logger.info(pos.prometheus.get_volume_state(array_name=array, volume_name=vol))
            assert pos.cli.delete_volume(array_name=array,volumename=vol)[0] == True
            logger.info(pos.prometheus.get_volume_state(array_name=array, volume_name=vol))
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_start_set_stop_telemetry_loop(array_fixture):
    pos = array_fixture
    try:
        for iter in range(10):
            assert pos.cli.start_telemetry()[0] == True
            logger.info(pos.cli.get_property()[1])
            assert pos.cli.set_property()[0] == True
            logger.info(pos.cli.get_property()[1])
            assert pos.cli.stop_telemetry()[0] == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
