import traceback
import pytest

from pos import POS
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

    assert pos.cli.list_volume(array_name=array_name)[0] == True
    for vol_name in pos.cli.vols:
        assert pos.cli.reset_volume_policy_qos(vol_name, array_name)[0] == True
        assert pos.cli.unmount_volume(vol_name, array_name)[0] == True
        assert pos.cli.delete_volume(vol_name, array_name)[0] == True

    logger.info("==========================================")


def teardown_module():
    logger.info("========= TEAR DOWN AFTER SESSION ========")
    pos.exit_handler(expected=True)


# List of maxiops and maxbw


qos_iops_bw = [
    (15, 5000),
    (5000, 100),
    (50, 10),
    (12, 50),
    (15.0, 100.0),
    (5000, 10),
]
fio_io_type = ["file", "block"]


@pytest.mark.regression
@pytest.mark.parametrize("max_iops, max_bw", qos_iops_bw)
@pytest.mark.parametrize("io_type", fio_io_type)
def test_qos_io_throttle(max_iops, max_bw, io_type):
    logger.info(
        f" ========== Test : test_qos_io_throttle[{max_iops}-{max_bw}-{io_type}] ============ "
    )
    try:
        assert pos.cli.create_volume(vol_name, "12GB", array_name)[0] == True

        assert (
            pos.cli.create_volume_policy_qos(vol_name, array_name, max_iops, max_bw)[0]
            == True
        )

        assert pos.target_utils.get_subsystems_list() == True
        for ss in pos.target_utils.ss_temp_list:
            nqn = ss if "array1" in ss else None
            if nqn:
                break

        assert pos.cli.mount_volume(vol_name, array_name, nqn)[0] == True

        assert (
            pos.client.nvme_connect(nqn, pos.target_utils.helper.ip_addr[0], "1158")
            == True
        )

        assert pos.client.nvme_list() == True
        nvme_devs = pos.client.nvme_list_out

        fio_cmd = (
            f"fio --name=sequential_write --ioengine=libaio --rw=write "
            "--iodepth=64 --direct=1 --bs=128k --size=1g"
        )
        mount_point = None
        if io_type == "file":  # Run File IO
            assert pos.client.create_File_system(nvme_devs, fs_format="xfs") == True
            out, mount_point = pos.client.mount_FS(nvme_devs)
            assert out == True
            io_mode = False  # Set False this to File IO
            assert (
                pos.client.fio_generic_runner(
                    mount_point, fio_user_data=fio_cmd, IO_mode=io_mode
                )[0]
                == True
            )
            assert pos.client.unmount_FS(mount_point) == True
            mount_point = None
        else:  # Run Block IO
            io_mode = True  # Set True for Block IO
            assert (
                pos.client.fio_generic_runner(
                    nvme_devs, fio_user_data=fio_cmd, IO_mode=io_mode
                )[0]
                == True
            )

        fio_out = {}
        fio_out["iops"] = pos.client.fio_par_out["write"]["iops"]
        fio_out["bw"] = pos.client.fio_par_out["write"]["bw"] / 1024  # Conver to MB

        # Verify the QOS Throttling
        assert (
            pos.client.fio_verify_qos(
                {"max_iops": max_iops, "max_bw": max_bw}, fio_out, len(nvme_devs)
            )
            == True
        )

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        if mount_point:
            assert pos.client.unmount_FS(mount_point) == True
        traceback.print_exc()
        assert 0
