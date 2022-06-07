import json

# from lib.pos import POS
import logger
import pytest
from pos import POS

logger = logger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_module():
    global pos, raid_type, data_dict
    raid_type = "raid10"
    pos = POS()
    data_dict = pos.data_dict
    data_dict["system"]["phase"] = "true"
    data_dict["device"]["phase"] = "true"
    data_dict["array"]["phase"] = "false"
    data_dict["subsystem"]["phase"] = "true"
    data_dict["array"]["num_array"] = 2
    data_dict["volume"]["array1"]["phase"] = "false"
    data_dict["volume"]["array2"]["phase"] = "false"
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


def test_Array_R10_R5_Rebuilding():
    """The purpose of this test case is to Create 2 arrays with RAID 10 and RAID 0. Delete both Arrays.
    Create new arrays with RAID 0 and RAID 10. Create 2 volumes of 1000 GB on each array, Connect initiator, run block IO.
    Start Rebuilding of second Array and it should not impact the Data integrity of first array."""

    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        raid_list = ["RAID10", "RAID5"]
        for index, array in enumerate(array_list):
            assert (
                pos.cli.autocreate_array(
                    buffer_name=f"uram{str(index)}",
                    num_spare=0 + index,
                    num_data=4 + index,
                    raid=raid_list[index],
                    array_name=array,
                )[0]
                == True
            )
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="100gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
        for array in array_list:
            assert pos.cli.list_volume(array_name=array)[0] == True
            for volume in pos.cli.vols:
                pos.cli.unmount_volume(volumename=volume, array_name=array)
                pos.cli.delete_volume(volumename=volume, array_name=array)
            assert pos.cli.info_array(array_name=array)[0] == True
            assert pos.cli.unmount_array(array_name=array)[0] == True
            assert pos.cli.delete_array(array_name=array)[0] == True
        for index, array in enumerate(array_list):
            assert (
                pos.cli.autocreate_array(
                    buffer_name=f"uram{str(index)}",
                    num_spare=1 - index,
                    num_data=5 - index,
                    raid=raid_list[index - 1],
                    array_name=array,
                )[0]
                == True
            )
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="100gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
        assert pos.cli.list_array()[0] == True
        assert pos.cli.list_device()[0] == True
        assert pos.cli.info_array(array_name="posarray1")[0] == True
        assert pos.target_utils.device_hot_remove(
            [pos.cli.array_info["posarray1"]["data_list"][0]]
        )
        assert pos.cli.info_array(array_name="posarray1")[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_16drive_2Array():
    """The purpose of this test case is to Create 2 Arrays using 16 Drives with RAID 10 option.
    Create 2 volumes of Max Size 5 TB on each array and Run Block IO to verify the data integrity."""

    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_spare=0 + index,
                num_data=14,
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="5000gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_Npor_R5():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity.
    Perform the NPOR operation, then create Array with RAID 5 option and run Block IO again and verify the data integrity."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            assert (
                pos.cli.autocreate_array(
                    buffer_name=f"uram{str(index)}",
                    num_spare=0,
                    num_data=4,
                    raid="RAID10",
                    array_name=array,
                )[0]
                == True
            )
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

        assert pos.target_utils.Npor() == True

        for index, array in enumerate(array_list):
            assert (
                pos.cli.autocreate_array(
                    buffer_name=f"uram{str(index)}",
                    num_spare=1,
                    num_data=5,
                    raid="RAID5",
                    array_name=array,
                )[0]
                == True
            )
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_R5():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity.
    Delete and Recreate Array with RAID 5 option, then Run Block IO again and verify the data integrity."""

    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_spare=0,
                num_data=4,
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
        for array in array_list:
            assert pos.cli.list_volume(array_name=array)[0] == True
            for volume in pos.cli.vols:
                pos.cli.unmount_volume(volumename=volume, array_name=array)
                pos.cli.delete_volume(volumename=volume, array_name=array)
            assert pos.cli.info_array(array_name=array)[0] == True
            assert pos.cli.unmount_array(array_name=array)[0] == True
            assert pos.cli.delete_array(array_name=array)[0] == True

        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_spare=1,
                num_data=5,
                raid="RAID5",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_Remove_Data_Spare():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity.
    Remove 1 data drive from array 1 and verify the rebuild process.
    Remove 1 spare drive and the array should go in Degraded state."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_data=4,
                num_spare="1",
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
        assert pos.cli.list_array()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.list_device()[0] == True
            assert pos.cli.info_array(array_name=array)[0] == True
            assert pos.target_utils.device_hot_remove(
                [pos.cli.array_info[array]["data_list"][0]]
            )

            assert pos.target_utils.device_hot_remove(
                [pos.cli.array_info[array]["spare_list"][0]]
            )
            assert pos.cli.info_array(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_RemoveSpare():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity.
    Add 1 spare drive to array 1 while IO is running."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_data=4,
                num_spare="1",
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
        assert pos.cli.list_array()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.list_device()[0] == True
            assert pos.cli.info_array(array_name=array)[0] == True
            assert pos.target_utils.device_hot_remove(
                [pos.cli.array_info[array]["spare_list"][0]]
            )
            assert pos.cli.info_array(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_Remove_Data():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity.
    Add 1 data drive to array 1 while IO is running."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_data=4,
                num_spare=0,
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
        assert pos.cli.list_array()[0] == True
        for array in list(pos.cli.array_dict.keys()):
            assert pos.cli.list_device()[0] == True
            assert pos.cli.info_array(array_name=array)[0] == True
            assert pos.target_utils.device_hot_remove(
                [pos.cli.array_info[array]["data_list"][0]]
            )
            assert pos.cli.info_array(array_name=array)[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_QoS_256vol():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 256 volumes with QOS policy set on each array and Run Block IO to verify the data integrity and QOS throttling."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_data=4,
                num_spare=0,
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=256, size="10gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            for volname in pos.cli.vols:
                assert pos.cli.create_volume_policy_qos(
                    arrayname=array, volumename=volname, maxiops=10, maxbw=10
                )
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_256vol():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 256 volumes on each array and Run Block IO to verify the data integrity."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_data=4,
                num_spare=0,
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=256, size="10gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_AutoCreate_R10():
    """The purpose of this test case is to Auto create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_data=4,
                num_spare=0,
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
        assert pos.cli.list_array()[0] == True

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_Npor():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity then Perform NPOR.
    Post NPOR the volumes should be back online."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            assert (
                pos.cli.autocreate_array(
                    buffer_name=f"uram{str(index)}",
                    num_spare=0,
                    num_data=4,
                    raid="RAID10",
                    array_name=array,
                )[0]
                == True
            )
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

        assert pos.target_utils.Npor() == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_Spor():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity then Perform SPOR."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            assert (
                pos.cli.autocreate_array(
                    buffer_name=f"uram{str(index)}",
                    num_spare=0,
                    num_data=4,
                    raid="RAID10",
                    array_name=array,
                )[0]
                == True
            )
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

        assert pos.target_utils.Spor() == True
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10_QoS_2vol():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes with QOS policy set on each array and Run Block IO to verify the data integrity and QOS throttling."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            res = pos.cli.autocreate_array(
                buffer_name=f"uram{str(index)}",
                num_data=4,
                num_spare=0,
                raid="RAID10",
                array_name=array,
            )
            assert res[0] == True
            logger.info(json.dumps(res[1], indent=1))
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="1000gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            for volname in pos.cli.vols:
                assert pos.cli.create_volume_policy_qos(
                    arrayname=array, volumename=volname, maxiops=10, maxbw=10
                )
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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

    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()


def test_Array_R10():
    """The purpose of this test case is to Create 2 Arrays using four Drive with RAID 10 option. Create 2 volumes on each array and Run Block IO to verify the data integrity."""
    try:
        # if previous TC failed load POS from start
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        # step 2 create 2 arrays as per config
        assert pos.cli.reset_devel()[0] == True
        array_list = ["posarray1", "posarray2"]
        for index, array in enumerate(array_list):
            assert (
                pos.cli.autocreate_array(
                    buffer_name=f"uram{str(index)}",
                    num_spare=0,
                    num_data=4,
                    raid="RAID10",
                    array_name=array,
                )[0]
                == True
            )
            assert pos.cli.mount_array(array_name=array)[0] == True
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name=array, num_vol=2, size="500gb", vol_name="vol"
                )
                == True
            )
            assert pos.target_utils.get_subsystems_list() == True
            assert pos.cli.list_volume(array_name=array)[0] == True
            ss_list = [ss for ss in pos.target_utils.ss_temp_list if array in ss]
            assert (
                pos.target_utils.mount_volume_multiple(
                    array_name=array, volume_list=pos.cli.vols, nqn_list=ss_list
                )
                == True
            )
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
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler()
