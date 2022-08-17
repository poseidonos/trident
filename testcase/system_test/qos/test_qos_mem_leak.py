from time import time
import pytest

from pos import POS
import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, raid_type, nr_data_drives, num_array
    pos = POS("pos_config.json")
    data_dict = pos.data_dict
    data_dict["subsystem"]["pos_subsystems"][0]["nr_subsystems"] = 1
    data_dict["subsystem"]["pos_subsystems"][1]["nr_subsystems"] = 1
    data_dict["volume"]["phase"] = "false",
    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True

    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")
    assert pos.target_utils.helper.check_system_memory() == True
    if pos.client.ctrlr_list()[1] is not None:
        assert pos.client.nvme_disconnect(pos.target_utils.ss_temp_list) == True

    assert pos.cli.list_array()[0] == True
    array_list = list(pos.cli.array_dict.keys())
    for array in array_list:
        assert pos.cli.list_volume(array_name=array)[0] == True
        for vol_name in pos.cli.vols:
            if pos.cli.vol_dict[vol_name]["status"] == "Mounted":
                assert pos.cli.unmount_volume(vol_name,
                                              array_name=array)[0] == True
            assert pos.cli.delete_volume(vol_name, array_name=array)[0] == True
    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


loop_action = [
    "set_reset_qos",        # set qos policy as step 2 and reset qos
    "mount_unmount_vol",    # mount and unmount volume
    "create_delete_vol",    # create and delete volume
    "nvme_connect_disconnect",      # nvme connect disconnect from initiator
    "mount_unmount_array",          # mount unmount array
]

@pytest.mark.regression
@pytest.mark.parametrize("action", loop_action)
def test_qos_mem_leak(action):
    logger.info(
        " ==================== Test : test_create_array3_after_array2_delete ================== "
    )
    try:
        vol_name_pre = "pos_vol"
        num_vols, vol_size = 2, "500gb"
        assert pos.target_utils.get_subsystems_list() == True
        ss_list = pos.target_utils.ss_temp_list[:2]

        assert pos.cli.list_array()[0] == True
        array_list = list(pos.cli.array_dict.keys())
        for id,array_name in enumerate(array_list):
            assert pos.target_utils.create_volume_multiple(array_name, num_vols,
                                                           vol_name_pre, 
                                                           size=vol_size) == True
            assert pos.cli.list_volume(array_name=array_name)[0] == True

            # Set the QOS values
            for vol_name in pos.cli.vols:
                assert pos.cli.create_volume_policy_qos(
                    vol_name, array_name, maxiops="10", maxbw="10")[0] == True

            if action != "create_delete_vol":
                nqn = [ss_list[id]]
                assert pos.target_utils.mount_volume_multiple(
                    array_name, pos.cli.vols, nqn_list=nqn) == True

        start_time = time()
        loop_time = 60 * 60         # 1 hour
        loop_counter = 0
        # Loop operation
        while ((time() - start_time) < loop_time):
            if action == "set_reset_qos":
                for array_name in array_list:
                    assert pos.cli.list_volume(array_name=array_name)[0] == True
                    for vol_name in pos.cli.vols:
                        assert pos.cli.reset_volume_policy_qos(
                            vol_name, array_name)[0] == True
                        assert pos.cli.create_volume_policy_qos(vol_name,
                            array_name, maxiops="10", maxbw="10")[0] == True

            elif action == "mount_unmount_vol":
                for id, array_name in enumerate(array_list):
                    assert pos.cli.list_volume(array_name=array_name)[0] == True
                    for vol_name in pos.cli.vols:
                        assert pos.cli.unmount_volume(
                            vol_name, array_name=array_name)[0] == True
                    nqn = [ss_list[id]]
                    assert pos.target_utils.mount_volume_multiple(
                        array_name, pos.cli.vols, nqn_list=nqn) == True

            elif action == "create_delete_vol":
                for array_name in array_list:
                    assert pos.cli.list_volume(array_name=array_name)[0] == True
                    for vol_name in pos.cli.vols:
                        assert pos.cli.delete_volume(vol_name, array_name)[0] == True

                    assert pos.target_utils.create_volume_multiple(
                        array_name, num_vols, vol_name_pre, size=vol_size) == True

            elif action == "nvme_connect_disconnect":
                for nqn in ss_list:
                    assert pos.client.nvme_connect(nqn, 
                           pos.target_utils.helper.ip_addr[0], "1158") == True

                assert pos.client.nvme_disconnect(ss_list) == True

            elif action == "mount_unmount_array":
                for array_name in array_list:
                    assert pos.cli.unmount_array(array_name=array_name)[0] == True

                for array_name in array_list:
                    assert pos.cli.mount_array(array_name=array_name)[0] == True

            loop_counter += 1
            if loop_counter == 100:
                assert pos.target_utils.helper.check_system_memory() == True
                loop_counter = 0

        logger.info(f"Memory Info: {pos.target_utils.helper.sys_memory_list}")

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

        