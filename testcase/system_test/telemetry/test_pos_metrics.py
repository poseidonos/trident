import time
from common_libs import *
import logger
import os
logger = logger.get_logger(__name__)

def array_and_volume_creation(pos,num_array=1,run_io=True):
    # Bring up arrays and volumes and run io
    pos.data_dict["array"]["num_array"] = num_array
    assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
    assert pos.cli.list_array()[0] == True
    arrays = list(pos.cli.array_dict.keys())
    assert pos.target_utils.get_subsystems_list() == True
    assert volume_create_and_mount_multiple(pos=pos, num_volumes=1, array_list=[arrays[0]],
                                            subs_list=pos.target_utils.ss_temp_list) == True
    if run_io == True:
        assert vol_connect_and_run_random_io(pos, pos.target_utils.ss_temp_list, size='1g') == True
    return arrays

@pytest.mark.parametrize("num_array",[1,2])
def test_verify_volume_states_and_capacity(array_fixture,num_array):
    pos = array_fixture
    try:
        #Set telemetry Configs
        assert pos.prometheus.set_telemetry_configs() == True
        pos.data_dict["array"]["num_array"] = 1
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 1
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        arrays = list(pos.cli.array_dict.keys())
        assert pos.cli.list_volume(array_name=arrays[0])[0] == True
        # array = arrays[0]
        vols = pos.cli.vols

        time.sleep(20)
        for array in arrays:
            assert pos.cli.info_array(array_name=array)[0] == True
            array_info = pos.cli.array_info[array]
            for vol in vols:
                #Verify volume total
                assert pos.cli.info_volume(array_name=array, vol_name=vol)[0] == True
                assert pos.prometheus.get_volume_capacity_total(array_name=arrays[0], volume_name=vol) \
                       == str(pos.cli.volume_info[arrays[0]][vol]['total_capacity']), "Total volume capacity does not match"

                time.sleep(20)

                assert pos.prometheus.get_volume_capacity_used(array_id=str(array_info['index']),
                                                               volume_id=str(pos.cli.vol_dict[vol]['index'])) \
                       == str( pos.cli.vol_dict[vol]['total'] - pos.cli.volume_info[arrays[0]][vol]['remain']),\
                       "Used volume capacity does not match"

                #Verfiy volume mounted state in metric
                assert pos.prometheus.volume_states[pos.prometheus.get_volume_state(array_name=array, volume_name=vol)] \
                       == pos.cli.vol_dict[vol]["status"].lower()

                #Unmount the volume
                assert pos.cli.unmount_volume(array_name=array,volumename=vol)[0] == True
                assert pos.cli.list_volume(array_name=array)[0] == True
                time.sleep(20)

                #Verify unmounted state in metrics
                assert pos.prometheus.volume_states[pos.prometheus.get_volume_state(array_name=array,volume_name=vol)] \
                       == pos.cli.vol_dict[vol]["status"].lower()

                #Delete the volume
                assert pos.cli.delete_volume(array_name=arrays[0],volumename=pos.cli.vols[0])[0] == True
                assert pos.cli.list_volume(array_name=array)[0] == True
                time.sleep(20)

                #Verify the offline state in metrics
                assert pos.prometheus.volume_states[pos.prometheus.get_volume_state(array_name=array, volume_name=vol)] \
                       == "offline"

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

def test_array_state_during_device_removal(array_fixture):
    pos = array_fixture
    array_states_dict = pos.prometheus.array_states
    try:
        #Start and Set telemetry property
        assert pos.prometheus.set_telemetry_configs() == True

        #Array Hot remove simultaneously and very array state
        arrays = array_and_volume_creation(pos=pos,num_array=2)
        for array in arrays:
            assert array_disks_hot_remove(pos=pos,array_name=array,disk_remove_interval_list=[(0,)]) == True
            assert pos.cli.info_array(array_name=arrays[0])[0] == True
            assert pos.prometheus.array_states[
                       pos.prometheus.get_array_state(uniqueid=pos.cli.array_info[arrays[0]]['uniqueId'])] \
                   == pos.cli.array_info[arrays[0]]['situation']
            assert pos.target_utils.array_rebuild_wait(array_name=array) == True
            assert pos.prometheus.array_states[
                       pos.prometheus.get_array_state(uniqueid=pos.cli.array_info[arrays[0]]['uniqueId'])] \
                   == pos.cli.array_info[arrays[0]]['situation']

    except Exception as e:
        logger.info(f"Testcase failed due to {e}")
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

@pytest.mark.negative
def test_set_telemetry_property(array_fixture):
    pos = array_fixture
    try:
        assert pos.cli.start_telemetry()[0] == True
        logger.info(pos.cli.get_property()[1])

        logger.info("***************Set Telemetry property with invalid filename***************")
        #Set property with a filename that is not present
        assert pos.cli.set_property(publication_list_path="/etc/pos/invalid_publicartion_file.yml")[0] == False

        logger.info("***************Set Telemetry property with invalid path***************")
        #Set property with a invalid file path
        assert pos.cli.set_property(publication_list_path="/etc/invalid_path/publication_file.yml")[0] == False

        logger.info("***************Set Telemetry property with invalid file format***************")
        #Set property with a txt file
        f = open("new_file.txt","w+")
        f.close()
        assert pos.cli.set_property(publication_list_path="new_file.txt")
        os.remove("new_file.txt")
    except Exception as e:
        logger.info(f"Testcase failed due to {e}")
        pos.exit_handler(expected=False)

def test_array_and_volume_capacity(array_fixture):
    pos = array_fixture
    try:
        assert pos.prometheus.set_telemetry_configs() == True

        arrays = array_and_volume_creation(pos,num_array=1)
        assert pos.cli.info_array(array_name=arrays[0])[0] == True
        array_info = pos.cli.array_info[arrays[0]]

        #Verify Array in Normal state
        assert pos.prometheus.array_states[pos.prometheus.get_array_state(uniqueid=array_info['uniqueId'])] == \
               array_info['situation']

        #Verify total array capacity
        assert pos.prometheus.get_total_array_capacity(array_id=str(array_info['index'])) == str(array_info['size'])

        #Verify the array used capacity
        assert pos.prometheus.get_used_array_capacity(array_id=str(array_info['index'])) == str(array_info['used'])


        assert pos.cli.list_volume(array_name=arrays[0])[0] == True
        for vol in list(pos.cli.vols):
            assert pos.cli.info_volume(array_name=arrays[0], vol_name=vol)[0] == True

            #Verify the total volume capacity
            assert pos.prometheus.get_volume_capacity_total(array_name=arrays[0], volume_name=vol) == str(
                pos.cli.volume_info[arrays[0]][vol]['total_capacity']), "Total volume capacity does not match"
            time.sleep(20)

            #Verify Volume Capacity used
            assert pos.prometheus.get_volume_capacity_used(array_id=str(array_info['index']),
                                                           volume_id=str(pos.cli.vol_dict[vol]['index'])) == str(
                pos.cli.vol_dict[vol]['total'] - pos.cli.volume_info[arrays[0]][vol]['remain']), "Used volume capacity does not match"

            #Verify the volume state
            assert pos.prometheus.volume_states[pos.prometheus.get_volume_state(array_name=arrays[0], volume_name=vol)] == \
                   pos.cli.volume_info[arrays[0]][vol]['status'].lower(), "Volume status does not match"
    except Exception as e:
        logger.info(f"Testcase failed due to {e}")
        pos.exit_handler(expected=False)

def test_array_capacity_after_volume_deletion(array_fixture):
    pos = array_fixture
    try:
        assert pos.prometheus.set_telemetry_configs() == True

        arrays = array_and_volume_creation(pos, num_array=1)
        assert pos.cli.info_array(array_name=arrays[0])[0] == True
        array_info = pos.cli.array_info[arrays[0]]

        # Verify the array used capacity
        assert pos.prometheus.get_used_array_capacity(array_id=str(array_info['index'])) == str(array_info['used'])

        assert pos.cli.list_volume(array_name=arrays[0])[0] == True
        for vol in list(pos.cli.vols):
            pos.cli.unmount_volume(volumename=vol,array_name=arrays[0])[0] == True
            pos.cli.delete_volume(volumename=vol,array_name=arrays[0])[0] == True

        # Verify the array used capacity after volume deleteion
        assert pos.prometheus.get_used_array_capacity(array_id=str(array_info['index'])) == str(array_info['used'])

    except Exception as e:
        logger.info(f"Testcase failed due to {e}")
        pos.exit_handler(expected=False)

def test_array_recreation_in_loop(array_fixture):
    pos = array_fixture
    try:
        assert pos.prometheus.set_telemetry_configs() == True
        for array in range(2):
            arrays = array_and_volume_creation(pos, num_array=1)
            assert pos.cli.info_array(array_name=arrays[0])[0] == True
            assert pos.prometheus.array_states[
                       pos.prometheus.get_array_state(uniqueid=pos.cli.array_info[arrays[0]]['uniqueId'])] \
                   == pos.cli.array_info[arrays[0]]['situation']
            assert pos.cli.list_volume(array_name=arrays[0])[0] == True
            vols = pos.cli.vols
            for vol in vols:
                assert pos.cli.pos_exporter(operation='start')[0] == True

                assert pos.cli.unmount_volume(array_name=array, volumename=vol)[0] == True
                assert pos.cli.list_volume(array_name=array)[0] == True
                time.sleep(20)

                # Verify unmounted state in metrics
                assert pos.prometheus.volume_states[pos.prometheus.get_volume_state(array_name=array, volume_name=vol)] \
                       == pos.cli.vol_dict[vol]["status"].lower()

                assert pos.cli.delete_volume(array_name=arrays[0], volumename=pos.cli.vols[0])[0] == True
                assert pos.cli.list_volume(array_name=array)[0] == True
                time.sleep(20)

                # Verify the offline state in metrics
                assert pos.prometheus.volume_states[pos.prometheus.get_volume_state(array_name=array, volume_name=vol)] \
                       == "offline"

            assert pos.cli.unmount_array(array_name=array)[0] == True

            assert pos.cli.info_array(array_name=arrays[0])[0] == True
            assert pos.prometheus.array_states[
                       pos.prometheus.get_array_state(uniqueid=pos.cli.array_info[arrays[0]]['uniqueId'])] \
                   == pos.cli.array_info[arrays[0]]['situation']

            assert pos.cli.delete_array(array_name=arrays[0])[0] == True
            assert pos.cli.info_array(array_name=arrays[0])[0] == True
            assert pos.prometheus.array_states[
                       pos.prometheus.get_array_state(uniqueid=pos.cli.array_info[arrays[0]]['uniqueId'])] \
                   == pos.cli.array_info[arrays[0]]['situation']

    except Exception as e:
        logger.info(f"Testcase failed due to {e}")
        pos.exit_handler(expected=False)