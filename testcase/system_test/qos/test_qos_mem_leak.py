from time import time
import pytest

import logger

logger = logger.get_logger(__name__)


loop_action = [
    "set_reset_qos",  # set qos policy as step 2 and reset qos
    "mount_unmount_vol",  # mount and unmount volume
    "create_delete_vol",  # create and delete volume
    "nvme_connect_disconnect",  # nvme connect disconnect from initiator
    "mount_unmount_array",  # mount unmount array
]


def set_reset_qos():
    for array_name in array_list:
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        for vol_name in pos.cli.vols:
            assert pos.cli.qos_reset_volume_policy(vol_name, array_name)[0] == True
            assert pos.cli.qos_create_volume_policy(vol_name, array_name,
                                            maxiops="10", maxbw="10")[0] == True

def mount_unmount_vol():
    for index, array_name in enumerate(array_list):
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        for vol_name in pos.cli.vols:
            assert pos.cli.volume_unmount(vol_name, array_name=array_name)[0] == True
        nqn = ss_list[index]
        assert pos.target_utils.mount_volume_multiple(array_name,
                                                      pos.cli.vols, nqn=nqn) == True

def nvme_connect_disconnect():
    ip_addr = pos.target_utils.helper.ip_addr[0]
    for nqn in ss_list:
        assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

    assert pos.client.nvme_disconnect(ss_list) == True


def create_delete_vol():
    for array_name in array_list:
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        for vol_name in pos.cli.vols:
            assert pos.cli.volume_delete(vol_name, array_name)[0] == True

        assert pos.target_utils.create_volume_multiple(array_name, num_vols,
                                        vol_name_pre, size=vol_size) == True

def mount_unmount_array():
    for array_name in array_list:
        assert pos.cli.array_unmount(array_name=array_name)[0] == True

    for array_name in array_list:
        assert pos.cli.array_mount(array_name=array_name)[0] == True

dict_func = {
    "set_reset_qos": set_reset_qos,
    "mount_unmount_vol": mount_unmount_vol,
    "create_delete_vol": create_delete_vol,
    "nvme_connect_disconnect": nvme_connect_disconnect,
    "mount_unmount_array": mount_unmount_array,
}


@pytest.mark.regression
@pytest.mark.parametrize("action", loop_action)
def test_qos_mem_leak(volume_fixture, action):
    logger.info(
        f" ==================== Test : test_qos_mem_leak[{action}] ================== "
    )
    try:
        global pos, data_dict, raid_type, nr_data_drives, num_array, array_list, ss_list, vol_name_pre, num_vols, vol_size
        pos = volume_fixture

        vol_name_pre = "pos_vol"
        num_vols, vol_size = 2, "500gb"
        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:2]
        for id, array_name in enumerate(array_list):
            assert pos.target_utils.create_volume_multiple(array_name, 
                            num_vols, vol_name_pre, size=vol_size) == True

            assert pos.cli.volume_list(array_name=array_name)[0] == True

            # Set the QOS values
            for vol_name in pos.cli.vols:
                assert pos.cli.qos_create_volume_policy(vol_name,
                            array_name, maxiops="10", maxbw="10")[0] == True

            if action != "create_delete_vol":
                nqn = ss_list[id]
                assert pos.target_utils.mount_volume_multiple(array_name, 
                                            pos.cli.vols, nqn=nqn) == True

        start_time = time()

        # TODO Read from the JSON
        loop_time = 60 * 60  # 1 hour
        loop_counter = 0
        # Loop operation
        while (time() - start_time) < loop_time:
            dict_func[action]()

            loop_counter += 1
            if loop_counter == 50:
                assert pos.target_utils.helper.check_system_memory() == True
                loop_counter = 0

        logger.info(f"Memory Info: {pos.target_utils.helper.sys_memory_list}")

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
