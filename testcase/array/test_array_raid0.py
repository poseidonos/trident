import pytest

#from lib.pos import POS
import logger
from pos import POS

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict, data_store
    raid_type = "raid0"
    pos = POS("array_raid0.json")
    data_store = {}
    data_dict = pos.data_dict
    # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos

def teardown_function():

    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    if len(array_list) == 0:
        logger.info("No array found in the config")
    else:
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True

    assert pos.cli.reset_devel()[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


def test_R0_2Array_BlockIO():
    try:
        logger.info(" ============== Test : test_R0_2Array_BlockIO =============")
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        array_list = [f'array{str(i)}' for i in range(1,3)]
        assert pos.cli.reset_devel()[0] == True
        for index,array in enumerate(array_list):
            assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid="RAID0", array_name= array)[0] == True
            assert pos.cli.mount_array(array_name = array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol']) == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
            
        assert pos.target_utils.get_subsystems_list() == True
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
            )[0]
            == True
        )
        logger.info(" ========================================== ")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected = False)

@pytest.mark.sanity
def test_R0_AutoCreateArray():
    try:
        logger.info("=================TESTs : test_R0_AutoCreateArray =============")
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        
        array_list = [f'array{str(i)}' for i in range(1,3)]
        assert pos.cli.reset_devel()[0] == True
        for index,array in enumerate(array_list):
            assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid="RAID0", array_name= array)[0] == True
            assert pos.cli.mount_array(array_name = array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol']) == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158") == True
            
        assert pos.client.nvme_list() == True
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out, fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10")[0] == True
             
        logger.info(" ========================================= ")
    except Exception as e:
        logger.error(f'Test script failed due to {e}')
        pos.exit_handler()
@pytest.mark.sanity
def test_R0_R5_Array_WriteThrough():
    try:
        logger.info("============= TEST : test_R0_R5_Array_WriteThrough ============")
        if pos.target_utils.helper.check_pos_exit() == True:
                     
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        array_list = [f'array{str(i)}' for i in range(1,3)]
        raid_list = ['RAID0', 'RAID5']
        assert pos.cli.reset_devel()[0] == True
        for index,array in enumerate(array_list):
              assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid=raid_list[index], array_name= array)[0] == True
              assert pos.cli.mount_array(array_name = array,write_back = False)[0] == True
              assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol']) == True
              assert pos.target_utils.get_subsystems_list() == True
              assert pos.cli.list_volume(array_name = array)[0] == True
              ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
              assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
        for ss in pos.target_utils.ss_temp_list:
              assert pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158") == True
            
        assert pos.client.nvme_list() == True
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out, fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10")[0] == True
        logger.info(" ================================================== ")    
    except Exception as e:
        logger.error(f'Test script failed due to {e}')
        pos.exit_handler()
@pytest.mark.sanity
@pytest.mark.parametrize('raid_type', ['RAID0', 'RAID5'])
def test_deleteR0_create_R5Array(raid_type):
    try:
        logger.info("===================== TEST : test_deleteR0_create_R5Array ============== ")
        #if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            pos.data_dict['array']['phase'] = 'false'
            pos.data_dict['volume']['array1']['phase'] = 'false'
            pos.data_dict['volume']['array2']['phase'] == 'false'
            
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        #step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = [f'array{str(i)}' for i in range(1,3)]
        for index,array in enumerate(array_list):
            assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid="RAID0", array_name= array)[0] == True
            assert pos.cli.mount_array(array_name = array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol']) == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158") == True
            
        #run Block IO    
        assert pos.client.nvme_list() == True
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out, fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10")[0] == True
        assert pos.client.nvme_disconnect() == True
        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        #Delete the arrays
        for array in array_list:
            assert pos.cli.info_array(array_name=array)[0] == True
            if pos.cli.array_dict[array].lower() == "mounted":
                assert pos.cli.unmount_array(array_name=array)[0] == True
                assert pos.cli.delete_array(array_name=array)[0] == True
        array_list = [f'array{str(i)}' for i in range(1,3)]
        #Create, mount, unmont and delete R5 arrays using the same drives
        for i in  range(5):
            for index,array in enumerate(array_list):
               assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid=raid_type, array_name= array)[0] == True
               assert pos.cli.mount_array(array_name = array)[0] == True
               assert pos.cli.unmount_array(array_name = array)[0] == True
               assert pos.cli.delete_array(array_name=array)[0] == True
        logger.info(" ================================================== ")  
    except Exception as e:
        logger.error(f'Test script failed due to {e}')
        pos.exit_handler()
@pytest.mark.sanity    
def test_Create_delete_R0_R5():
    """The purpose of this test case is to Create 2 arrays with Raid 0, Create 2 volumes each, Delete first array and create first array with RAID 5 and create volumes on it.
    """
    try:
        logger.info(" ================= TEST : test_Create_delete_R0_R5 ==============")
        if pos.target_utils.helper.check_pos_exit() == True:
            
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        assert pos.cli.reset_devel()[0] == True
        array_list = [f'array{str(i)}' for i in range(1,3)]
        for index,array in enumerate(array_list):
            assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid="RAID0", array_name= array)[0] == True
            assert pos.cli.mount_array(array_name = array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol']) == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158") == True
            
        assert pos.client.nvme_list() == True
        
        assert pos.client.fio_generic_runner(pos.client.nvme_list_out, fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --size=100%")[0] == True
        assert pos.client.nvme_disconnect() == True
        assert pos.cli.info_array(array_name="array1")[0] == True
        assert pos.cli.unmount_array(array_name="array1")[0] == True
        assert pos.cli.delete_array(array_name="array1")[0] == True
        assert pos.cli.autocreate_array(buffer_name=f'uram0', num_data = pos.data_dict['array']['array1_data_count'],raid="RAID5", array_name= "array1")[0] == True
        logger.info(" ================================================== ")
        
    except Exception as e:
        logger.error(f'Test script failed due to {e}')
        pos.exit_handler()
@pytest.mark.sanity    
def test_Create_R0_Do_GC():
    """The purpose of this test case is to Create 2 arrays with Raid 0, Create 2 volumes on each, connect Initiator and Run block IO and Trigger Gc and verify the system response """
    try:
        logger.info(" =============== TEST : test_Create_R0_Do_GC ===================")
        #if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        #step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = [f'array{str(i)}' for i in range(1,3)]
        for index,array in enumerate(array_list):
            assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid="RAID0", array_name= array)[0] == True
            assert pos.cli.mount_array(array_name = array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol'], size = "10gb") == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --ioengine=libaio --rw=write --bs=16384 --iodepth=512 --direct=1  --numjobs=1 --verify=pattern --verify_pattern=0x5279e55fe853debd --do_verify=1 --verify_dump=1 --verify_fatal=1 --group_reporting  --log_offset=1 --name=pos0 --size=100% ",
            )[0]
            == True
        )
        assert pos.cli.wbt_do_gc()[0] == False
        logger.info(" ================================================== ")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected = False)
    

@pytest.mark.sanity            
def test_AddSpare_R0_Array():
    """The purpose of this test case is to Create 2 arrays with Raid 0, Create 2 volumes on each, Try to add spare to the existing Array and get the proper response for Raid 0 has no fault tolerance"""
    try:
        logger.info(" ================= TEST : test_AddSpare_R0_Array ================== ")
        #if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        #step 2 create 2 arrays as per config
        array_list = [f'array{str(i)}' for i in range(1,3)]
        for index,array in enumerate(array_list):
            assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid="RAID0", array_name= array)[0] == True
            assert pos.cli.mount_array(array_name = array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol']) == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
            )[0]
            == True
        )
        
        assert pos.cli.list_array()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.list_device()[0] == True
            assert pos.cli.addspare_array(pos.cli.system_disks[0], array_name = array)[0] == False
            assert pos.cli.info_array(array_name= array)[0] == True
        logger.info(" ================================================== ")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected = False)
@pytest.mark.sanity        
def test_remove_device_R0_Array():
    """The purpose of this test case is to Create 2 array with Raid 0 , Create 2 volumes on each , Detach 1 data drive and verify the array list and system response(System should not crash)"""
    try:
        logger.info("================ TEST : test_remove_device_R0_Array ==================")
       #if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict = pos.data_dict) == True
        #step 2 create 2 arrays as per config
        array_list = [f'array{str(i)}' for i in range(1,3)]
        for index,array in enumerate(array_list):
            assert pos.cli.autocreate_array(buffer_name=f'uram{str(index)}', num_data = pos.data_dict['array'][f'array{str(index+1)}_data_count'],raid="RAID0", array_name= array)[0] == True
            assert pos.cli.mount_array(array_name = array)[0] == True
            assert pos.target_utils.create_volume_multiple(array_name = array, num_vol = pos.data_dict['volume'][f'array{str(index+1)}']['num_vol']) == True
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name = array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert pos.target_utils.mount_volume_multiple(array_name= array,volume_list= pos.cli.vols, nqn_list = ss_list) == True
        for ss in pos.target_utils.ss_temp_list:
            assert pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158") == True
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data="fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime=10",
            )[0]
            == True)
        assert pos.cli.list_array()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.list_device()[0] == True
            assert pos.cli.info_array(array_name = array)[0] == True
            assert pos.target_utils.device_hot_remove([pos.cli.array_info[array]['data_list'][0]])
            assert pos.cli.info_array(array_name= array)[0] == True
        logger.info(" ================================================== ")
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected = False)
    
