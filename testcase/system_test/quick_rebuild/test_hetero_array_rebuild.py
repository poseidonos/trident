import pytest
import traceback

from common_libs import *

import logger
logger = logger.get_logger(__name__)

@pytest.fixture(scope="module")
def setup_cleanup_module():
    logger.info("========= SETUP MODULE ========")
    pos = POS("pos_config.json")

    data_dict = pos.data_dict
    data_dict["array"]["phase"] = "false"
    data_dict["volume"]["phase"] = "false"
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    assert pos.cli.devel_resetmbr()[0] == True

    yield pos

    logger.info("========= CLEANUP MODULE ========")
    pos.exit_handler(expected=True)

@pytest.fixture(scope="function")
def setup_cleanup_function(setup_cleanup_module):
    logger.info("========== SETUP BEFORE TEST =========")
    pos = setup_cleanup_module

    yield pos

    logger.info("========== CLEANUP AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.array_list()[0] == True
    for array in pos.cli.array_dict.keys():
        assert pos.cli.array_info(array_name=array)[0] == True
        if pos.cli.array_dict[array].lower() == "mounted":
            assert pos.cli.array_unmount(array_name=array)[0] == True
        assert pos.cli.array_delete(array_name=array)[0] == True

    logger.info("==========================================")


test_operations = {"t0": ("hetero", "RAID5", "RAID6", "vol_rename"),
                   "t1": ("hetero", "RAID5", "RAID10", "vol_unmount_mount"),
                   "t2": ("hetero", "RAID6", "RAID10", "array_unmount_mount"),
                   "t3": ("normal", "RAID5", "RAID6", "vol_unmount_mount")}
@pytest.mark.regression
@pytest.mark.parametrize("test_param", test_operations)
def test_hetero_array_qos_after_disk_replace(array_fixture, test_param):
    """
    Test to create two arrays RAID5, RAID6 arrays with minimum number of supported devices.
    Create and mount 2 volumes and set qos values. 
    """
    logger.info(
        f" ==================== Test :  test_hetero_array_qos_after_disk_replace[{test_param}] ================== "
    )
    try:
        pos = array_fixture
        array_type, aray1_raid, array2_raid, action = test_operations[test_param]
        raid_type_list = (aray1_raid, array2_raid)
        num_spare_disk = 2
        num_vols = 2

        hetero_array = False if (array_type == "normal") else True
        assert create_mount_hetero_arrays(pos, raid_type_list, num_spare_disk,
                                          hetero_array=hetero_array) == True

        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert volume_create_and_mount_multiple(pos, num_vols, 
                            array_list=array_list, subs_list=subs_list) == True

        maxiops, maxbw = 10, 10
        for array in array_list:
            assert pos.cli.volume_list(array_name=array)[0] == True
            for volname in pos.cli.vols:
                assert pos.cli.qos_create_volume_policy(arrayname=array, 
                    volumename=volname, maxiops=maxiops, maxbw=maxbw)[0] == True

        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = "fio --name=test_seq_write --ioengine=libaio --iodepth=32 --rw=write --size=50g --bs=32k --direct=1"

        assert pos.client.fio_generic_runner(nvme_devs, fio_user_data=fio_cmd)[0] == True

        fio_out = {}
        fio_out["iops"] = pos.client.fio_par_out["write"]["iops"]
        fio_out["bw"] = pos.client.fio_par_out["write"]["bw"] / 1024  # Conver to MB

        # Verify the QOS Throttling
        assert pos.client.fio_verify_qos({"max_iops":maxiops, "max_bw":maxbw},
                                         fio_out,
                                         len(nvme_devs)) == True

        assert do_action(pos, action, array_list, subs_list, maxiops, maxbw) == True

        # Array disk replace
        assert array_disk_remove_replace(pos, array_list, replace=True) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.regression
@pytest.mark.parametrize("array_disk_type", ["hetero", "normal"])
def test_array_disk_replace_multiple(array_fixture, array_disk_type):
    """
    Test to create two arrays RAID5, RAID6 arrays with minimum number of supported devices.
    Create and mount 2 volumes. During IO fail a data disk. 
    """
    logger.info(
        f" ==================== Test :  test_array_disk_replace_multiple[{array_disk_type}] ================== "
    )
    try:
        pos = array_fixture
        raid_type_list = [("RAID5", "RAID6"), ("RAID6", "RAID10")]
        num_spare_disk = 2
        array_cap_volumes = [(32, 100), (128, 100), (256, 100)]

        hetero_array = False if (array_disk_type == "normal") else True

        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list

        for repeat in range(4):
            # Create the array with differnt raid
            raid_type_list[(repeat % 2)]
            assert create_mount_hetero_arrays(pos, raid_type_list, num_spare_disk, 
                                              hetero_array=hetero_array) == True

            assert pos.cli.array_list()[0] == True
            array_list = list(pos.cli.array_dict.keys())

            assert volume_create_and_mount_random(pos, array_list=array_list,
                subsyste_list=subs_list, arr_cap_vol_list=array_cap_volumes) == True

            assert vol_connect_and_run_random_io(pos, subs_list, size='5g') ==  True

            # Array disk Fail or Hot Remove
            assert array_disk_remove_replace(pos, array_list, replace=False) == True

            # Array disk replace
            assert array_disk_remove_replace(pos, array_list, replace=True) == True

            # Delete Array
            assert array_unmount_and_delete(pos, unmount=True, delete=True) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


def do_action(pos, action, array_list, subs_list, maxiops, maxbw):
    if action == "vol_rename":
        res = rename_volumes(pos, array_list, maxiops, maxbw)
    elif action == "vol_unmount_mount":
        res = unmount_mount_volume(pos, array_list, subs_list, maxiops, maxbw)
    elif action == "array_unmount_mount":
        res = unmount_mount_array(pos, array_list, maxiops, maxbw)
    return res

def rename_volumes(pos, array_list, maxiops, maxbw):
    try:
        for array in array_list:
            assert pos.cli.volume_list(array_name=array)[0] == True
            for volname in pos.cli.vols:
                new_volname = f"new_{volname}"
                assert pos.cli.volume_rename(new_volname, volname, array_name=array)[0] == True
                assert verify_vol_qos_values(pos, array, new_volname, maxiops, maxbw) == True
        return True
    except Exception as e:
        logger.info(f"Failed to rename the volume due to {e}")
        return False

def unmount_mount_volume(pos, array_list, subs_list, maxiops, maxbw):
    try:
        for array in array_list:
            assert pos.cli.volume_list(array_name=array)[0] == True
            for volname in pos.cli.vols:
                ss_list = [ss for ss in subs_list if array in ss]
                assert pos.cli.volume_unmount(volname, array_name=array)[0] == True
                assert pos.cli.volume_mount(volname, array_name=array, nqn=ss_list[0])[0] == True
                assert verify_vol_qos_values(pos, array, volname, maxiops, maxbw) == True
        return True
    except Exception as e:
        logger.info(f"Failed to rename the volume due to {e}")
        return False

def unmount_mount_array(pos, array_list, maxiops, maxbw):
    try:
        for array in array_list:
            assert pos.cli.array_unmount(array_name=array)[0] == True
            assert pos.cli.array_mount(array_name=array, write_back=False)[0] == True
            assert pos.cli.volume_list(array_name=array)[0] == True
            for volname in pos.cli.vols:
                assert verify_vol_qos_values(pos, array, volname, maxiops, maxbw) == True
        return True
    except Exception as e:
        logger.info(f"Failed to rename the volume due to {e}")
        return False

def verify_vol_qos_values(pos, array_name, vol_name, maxiops, maxbw):
    try:
        assert pos.cli.volume_info(array_name=array_name, vol_name=vol_name)[0] == True
        assert pos.cli.volume_data[array_name][vol_name]["max_iops"] == maxiops
        assert pos.cli.volume_data[array_name][vol_name]["max_bw"] == maxbw
    except Exception as e:
        logger.info(f"Failed to verify volume qos values due to {e}")
        return False
    return True

def create_mount_hetero_arrays(pos, raid_list, num_spare_disk, hetero_array=True):
    try:
        req_disk_list = [RAID_MIN_DISK_REQ_DICT[r] for r in raid_list]
        min_req_disks = sum(req_disk_list) + 2 * num_spare_disk
        assert pos.cli.device_list()[0] == True

        # Verify the minimum disk requirement
        if len(pos.cli.system_disks) < min_req_disks:
            logger.info("Insufficient system disks {}. Required minimum{}".format(
                        len(pos.cli.system_disks), min_req_disks))
            pytest.skip()

        data_dict = pos.data_dict
        for index, raid_type in enumerate(raid_list):
            array_name = data_dict["array"]["pos_array"][index]["array_name"]
            uram_name = data_dict["device"]["uram"][index]["uram_name"]
            raid_type = raid_list[index]
            num_devs = RAID_MIN_DISK_REQ_DICT[raid_type]

            if hetero_array:
                data_device_conf = {'mix': 2, 'any': num_devs - 2}
            else:
                data_device_conf = {'any': num_devs}
            spare_device_conf = {'any': num_spare_disk}

            if not pos.target_utils.get_hetero_device(data_device_conf,
                                    spare_device_config=spare_device_conf):
                logger.info("Failed to get the required hetero devcies")
                pytest.skip("Required condition not met. Refer to logs for more details")

            data_drives = pos.target_utils.data_drives
            spare_drives = pos.target_utils.spare_drives

            assert pos.cli.array_create(write_buffer=uram_name, data=data_drives, 
                                        spare=spare_drives, raid_type=raid_type,
                                        array_name=array_name)[0] == True
            assert pos.cli.array_mount(array_name=array_name,
                                       write_back=False)[0] == True
    except Exception as e:
        logger.info(f"Failed to create and mount array due to {e}")
        return False
    return True
