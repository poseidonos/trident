import pytest
import re

from pos import POS

import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict
    pos = POS("volume_config.json")
    data_dict = pos.data_dict
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


def test_mounted_vol_info():
    array_name = pos.data_dict["array"]["array_name"]
    array_name = "array1"
    assert pos.cli.list_volume(array_name)[0] == True

    for vol in pos.cli.vols:
        assert pos.cli.info_volume(array_name, vol)[0] == True

        # Verify volume name and array name
        assert pos.cli.volume_info[array_name][vol]["name"] == vol
        assert pos.cli.volume_info[array_name][vol]["array_name"] == array_name

        # Verify the volume status is mounted
        assert pos.cli.volume_info[array_name][vol]["status"] == "Mounted"

        # Compare Volume Subnqn
        subnqn = "nqn.2022-10.posarray1:subsystem1"
        assert pos.cli.volume_info[array_name][vol]["subnqn"] == subnqn

        # Match volume's UUID
        vol_uuid = pos.cli.volume_info[array_name][vol]["uuid"]
        assert re.search(r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}", vol_uuid)

        # Compare the QOS values
        max_iops = pos.data_dict["volume"]["array1"]["qos"]["maxiops"]
        min_iops = pos.data_dict["volume"]["array1"]["qos"]["miniops"]
        max_bw = pos.data_dict["volume"]["array1"]["qos"]["maxbw"]
        min_bw = pos.data_dict["volume"]["array1"]["qos"]["minbw"]

        assert pos.cli.volume_info[array_name][vol]["max_bw"] == max_bw
        assert pos.cli.volume_info[array_name][vol]["min_bw"] == min_bw
        assert pos.cli.volume_info[array_name][vol]["max_iops"] == max_iops
        assert pos.cli.volume_info[array_name][vol]["min_iops"] == min_iops
