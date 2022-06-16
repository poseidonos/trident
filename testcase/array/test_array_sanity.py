import pytest
import random
import logger
from pos import POS

logger = logger.get_logger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, raid_type, data_dict, data_store
    pos = POS()
    data_store = {}
    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["array"]["num_array"] = 2
    data_dict["volume"]["array1"]["phase"] = "false"
    data_dict["volume"]["array2"]["phase"] = "false"
       # bring devices to user mode, setup core, setup udev, setup max map count
    # assert pos.target_utils.setup_env_pos() == True
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    assert pos.cli.reset_devel()[0] == True
    
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
    assert pos.target_utils.pci_rescan() == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)

raid = {"RAID0": {"spare" : 0, "data" : 2},
        "RAID10" : {"spare" : 2, "data" : 2 },
        "no-raid" : {"spare" : 0,  "data" : 1},
        "RAID5" : {"spare" : 1, "data" : 3}
        }

@pytest.mark.sanity
@pytest.mark.parametrize("writeback" , [True, False])
@pytest.mark.parametrize("raid_type", list(raid.keys()))
@pytest.mark.parametrize("numvol", [1,256])
@pytest.mark.parametrize("fioruntime", [10])
@pytest.mark.parametrize("spor", [False]) #To enable SPOR add True in the list
def test_SanityArray(raid_type, writeback, numvol, fioruntime, spor):
    try:
                    
        logger.info(f" ============== Test : RAID {raid_type} writeback {writeback} numvol {numvol} fioruntime {fioruntime} SPOR {spor} =============")
        if spor == False:
            logger.info("NPOR will be triggered in the Test")
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
            assert pos.cli.reset_devel()[0] == True
            assert pos.target_utils.pci_rescan() == True
        assert pos.cli.list_device()[0] == True
        datalen = raid[raid_type]['data']
        sparelen = raid[raid_type]['spare']
        datalist = pos.cli.dev_type['SSD'][0:datalen]
        sparelist = [] if sparelen == 0 else pos.cli.dev_type['SSD'][-sparelen:]
        assert pos.cli.create_array(array_name="array1", data=datalist, write_buffer= pos.cli.dev_type['NVRAM'][0], raid_type= raid_type,spare = sparelist)[0] == True
        array2raid = random.choice(list(raid.keys()))
        datalen = raid[array2raid]['data']
        sparelen = raid[array2raid]['spare']
        assert pos.cli.autocreate_array(array_name='array2', num_data=datalen, num_spare=sparelen, buffer_name=pos.cli.dev_type['NVRAM'][1], raid= array2raid)[0] == True
        
        assert pos.cli.list_device()[0] == True
        assert pos.target_utils.get_subsystems_list() == True
        #assert pos.cli.start_telemetry()[0] == True
        for index,array in enumerate(["array1", "array2"]):
            assert pos.cli.mount_array(array_name=array, write_back=writeback)[0] == True
           
            assert pos.target_utils.create_volume_multiple(array_name=array, num_vol=numvol, size = None) == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            assert pos.target_utils.mount_volume_multiple(array_name=array, volume_list=pos.cli.vols, nqn_list=[pos.target_utils.ss_temp_list[index]]) == True
        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )

        # run Block IO
        assert pos.client.nvme_list() == True
        assert (
            pos.client.fio_generic_runner(
                pos.client.nvme_list_out,
                fio_user_data=f"fio --name=sequential_write --ioengine=libaio --rw=write --iodepth=64 --direct=1 --numjobs=1 --bs=128k --time_based --runtime={fioruntime}",
            )[0]
            == True
        )
        
        assert pos.client.nvme_disconnect() == True
        assert pos.cli.info_array(array_name="array1")[0] == True
        if raid_type not in ["RAID0","no-raid"]:
             assert pos.cli.addspare_array(array_name="array1", device_name = pos.cli.array_info["array1"]["data_list"][0])[0] == False
             assert pos.cli.list_device()[0] == True
             assert pos.cli.addspare_array(array_name="array1", device_name = pos.cli.system_disks[0])[0] == True
             
        
        ## Create3rd array/ duplicate array
        assert pos.cli.create_array(array_name="array1", data=datalist, write_buffer= pos.cli.dev_type['NVRAM'][0], raid_type= raid_type,spare = sparelist)[0] == False
        assert pos.cli.autocreate_array(array_name='array2', num_data=datalen, num_spare=sparelen, buffer_name=pos.cli.dev_type['NVRAM'][1], raid= array2raid)[0] == False
        assert pos.cli.autocreate_array(array_name='array3', num_data=datalen, num_spare=sparelen, buffer_name=pos.cli.dev_type['NVRAM'][1], raid= array2raid)[0] == False
        
        for array in ["array1", "array2"]:
            writechoice = random.choice([True, False])
            assert pos.cli.mount_array(array_name=array, write_back=writechoice)[0] == False
            assert pos.cli.delete_array(array_name=array)[0] == False
        if spor == True:
            assert pos.target_utils.Spor() == True
        else:
            assert pos.target_utils.Npor() == True
        arrayname = "array1"
        assert pos.cli.info_array(array_name=arrayname)[0] == True
        if raid_type not in ["RAID0","no-raid"]:
             disklist = [random.choice(pos.cli.dev_type['SSD'])]
             assert pos.target_utils.device_hot_remove(disklist) == True
             #assert pos.cli.unmount_array(array_name=arrayname)[0] == False
             #assert pos.cli.delete_array(array_name=array)[0] == False
             assert pos.target_utils.array_rebuild_wait(array_name=arrayname) == True
    
        assert pos.cli.info_array(array_name=arrayname)[0] == True
        
        assert pos.cli.unmount_array(array_name=arrayname)[0] == True
        assert pos.cli.delete_array(array_name=arrayname)[0] == True
        assert pos.cli.list_array()[0] == True         
        #assert pos.cli.stop_telemetry()[0] == True    
        
    except Exception as e:
        logger.error(f" ======= Test FAILED : RAID {raid_type} writeback {writeback} numvol {numvol} fioruntime {fioruntime} SPOR {spor} ========")
    
    
 
