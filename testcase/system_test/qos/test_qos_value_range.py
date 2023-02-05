from time import time
import traceback
import pytest

import logger

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():

    global pos, data_dict, array_name, vol_name
    pos = POS("pos_config.json")
    data_dict = pos.data_dict

    data_dict["subsystem"]["pos_subsystems"][0]["nr_subsystems"] = 1
    data_dict["subsystem"]["pos_subsystems"][1]["nr_subsystems"] = 0

    data_dict["array"]["num_array"] = 1
    data_dict["volume"]["phase"] = "false"

    array_name = data_dict["array"]["pos_array"][0]["array_name"]
    vol_name = "POS_Vol"

    assert pos.target_utils.pos_bring_up(data_dict=data_dict) == True
    yield pos


def teardown_function():
    logger.info("========== TEAR DOWN AFTER TEST =========")

    assert pos.cli.volume_list(array_name=array_name)[0] == True
    for vol_name in pos.cli.vols:
        assert pos.cli.qos_reset_volume_policy(vol_name, array_name)[0] == True
        assert pos.cli.volume_delete(vol_name, array_name)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


# List of maxiops and maxbw

qos_tests = {}
# negative and decimals values for bandwidth
qos_tests["t0"] = {"iops_bw": [(0, -1.0), (0, 5.5), (0, 15.5)], "result": False}
# bandwidth values-1=9 and any iops
qos_tests["t1"] = {"iops_bw": [(0, 9), (10, 9), (100, 9)], "result": False}
# bandwidth=2^64-1 and iops 0, 10
qos_tests["t2"] = {"iops_bw": [(0, 2 ^ 64 - 1), (10, 2 ^ 64 - 1)], "result": True}
# bandwidth value=10 and any iops values
qos_tests["t3"] = {"iops_bw": [(0, 10), (10, 10), (100, 10)], "result": True}
# 0 iops and any maxbw values
qos_tests["t4"] = {"iops_bw": [(0, 15), (0, 100), (0, 1024)], "result": True}
# negative and decimals values for iops
qos_tests["t5"] = {"iops_bw": [(-1.0, 0), (5.5, 0), (15.5, 10)], "result": False}
# maxiops values-1=9 and maxbw values
qos_tests["t6"] = {"iops_bw": [(9, 0), (9, 10), (9, 1024)], "result": False}
# maxiops values=2^64-1  and maxbw 10
qos_tests["t7"] = {"iops_bw": [(2 ^ 64 - 1, 0), (2 ^ 64 - 1, 10)], "result": True}
# maxiops values=10  and maxbw values
qos_tests["t8"] = {"iops_bw": [(10, 0), (10, 10), (10, 1024)], "result": True}
# maxiops and maxbw values using
qos_tests["t9"] = {"iops_bw": [(15, 15), (1024, 1024), (100, 100)], "result": True}

qos_test_list = ["t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"]


@pytest.mark.regression
@pytest.mark.parametrize("qos_test", qos_test_list)
def test_qos_maxiops_maxbw_value(volume_fixture, qos_test):
    logger.info(
        f" ==================== Test : test_qos_maxiops_maxbw_value[{qos_test}] ================== "
    )
    try:
        pos = volume_fixture
        array_name = data_dict["array"]["pos_array"][0]["array_name"]
        vol_name = "POS_Vol"
        qos_values = qos_tests[qos_test]["iops_bw"]
        exp_result = qos_tests[qos_test]["result"]

        assert pos.cli.volume_create(vol_name, "10GB", array_name)[0] == True

        for max_iops, max_bw in qos_values:
            assert (
                pos.cli.qos_create_volume_policy(
                    vol_name, array_name, max_iops, max_bw
                )[0]
                == exp_result
            )

            if exp_result:
                assert (
                    pos.cli.volume_info(array_name=array_name, vol_name=vol_name)[0]
                    == True
                )

                vol_info = pos.cli.volume_data[array_name][vol_name]
                assert vol_info["max_iops"] == max_iops
                assert vol_info["max_bw"] == max_bw

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        assert 0


qos_iops_bw_res = [
    (0, 100, True),
    (100, 9, False),
    (9, 100, False),
    (100, 2 ^ 64 - 1, True),
    (100, 18446744073709551615, False),
    (18446744073709551615, 100, False),
    (100, 17592186044415, True),
    (100, 11, True),
    (10, 100, True),
    (100, 0, True),
    (100, 10, True),
]


@pytest.mark.regression
@pytest.mark.parametrize("max_iops, max_bw, exp_result", qos_iops_bw_res)
def test_vol_create_with_qos_value(volume_fixture, max_iops, max_bw, exp_result):
    logger.info(
        f" ================== Test : test_vol_create_with_qos_value"
        f"[{max_iops}-{max_bw}-{exp_result}] ===================== "
    )
    try:
        pos = volume_fixture
        array_name = data_dict["array"]["pos_array"][0]["array_name"]
        vol_name = "POS_Vol"
        assert (
            pos.cli.volume_create(
                vol_name, "10GB", array_name, iops=max_iops, bw=max_bw
            )[0]
            == exp_result
        )

        if exp_result:
            assert (
                pos.cli.volume_info(array_name=array_name, vol_name=vol_name)[0] == True
            )

            vol_info = pos.cli.volume_data[array_name][vol_name]
            assert vol_info["max_iops"] == max_iops
            assert vol_info["max_bw"] == max_bw

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        traceback.print_exc()
        assert 0
