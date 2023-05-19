import pytest

from common_libs import *

import logger
logger = logger.get_logger(__name__)

@pytest.mark.sanity
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_create_raid6_array(array_fixture, array_mount):
    """
    The purpose of this test is to create RAID 6 array with different data disk and spare disk.
    It includes the positive and negative test.
    Verification: POS CLI - Create Array Mount Array and List Array command.
    """
    logger.info(
        f" ==================== Test : test_create_raid6_array[{array_mount}] ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks

        array_disks = [(4, 0), (4, 1), (4, 2), (8, 2), (16, 2), (3, 0), (2, 2)]
        for data_disk, spare_disk in array_disks:
            if (data_disk + spare_disk) > len(system_disks):
                logger.warning("Insufficient system disks to test array create")
                continue
            
            exp_res = False if data_disk < RAID6_MIN_DISKS else True

            auto_create = False
            assert single_array_data_setup(pos.data_dict, "RAID6", data_disk,
                                spare_disk, array_mount, auto_create) == True

            assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == exp_res

            if exp_res:
                assert array_unmount_and_delete(pos) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)

@pytest.mark.sanity
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_auto_create_raid6_array(array_fixture, array_mount):
    """
    The purpose of this test is to create RAID 6 array with different data disk and spare disk.
    It includes the positive and negative test.
    Verification: POS CLI - Create Array Mount Array and List Array command.
    """
    logger.info(
        f" ==================== Test : test_auto_create_raid6_array[{array_mount}] ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks

        array_disks = [(4, 0), (4, 1), (4, 2), (3, 2), (2, 2)]
        for data_disk, spare_disk in array_disks:
            if (data_disk + spare_disk) > len(system_disks):
                logger.warning("Insufficient system disks to test array create")
                continue
            
            exp_res = False if data_disk < RAID6_MIN_DISKS else True

            auto_create = True
            assert single_array_data_setup(pos.data_dict, "RAID6", data_disk,
                                spare_disk, array_mount, auto_create) == True

            assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == exp_res

            if exp_res:
                array_name = pos.data_dict["array"]["pos_array"][0]["array_name"]
                assert pos.cli.array_info(array_name=array_name)[0] == True

                assert array_unmount_and_delete(pos) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)


@pytest.mark.sanity
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
def test_array_cap_with_volumes(array_fixture, array_mount):
    """
    The purpose of this test is to create RAID 6 array with different volumes and utilize its capacity.
    Verification: POS CLI - Array - Create, Mount, and List: Volume - Create, Mount, List
    """
    logger.info(
       f" ==================== Test : test_raid6_array_cap_with_volumes[{array_mount}] ================== "
    )
    pos = array_fixture
    try:
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < RAID6_MIN_DISKS:
            pytest.skip("Less number of data disk")

        auto_create = False
        assert single_array_data_setup(pos.data_dict, "RAID6", RAID6_MIN_DISKS,
                                       0, array_mount, auto_create) == True

        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert pos.cli.array_list()[0] == True
        array_list = list(pos.cli.array_dict.keys())

        assert pos.target_utils.get_subsystems_list() == True
        subsyste_list = pos.target_utils.ss_temp_list

        array_cap_volumes = [(1, 50), (1, 100), (1, 105), (50, 105), (256, 100), (257, 100)]

        for num_volumes, cap_utilize in array_cap_volumes:
            assert volume_create_and_mount_multiple(pos, num_volumes, cap_utilize,
                            array_list=array_list, subs_list=subsyste_list) == True

            assert volume_unmount_and_delete_multiple(pos, array_list) == True
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)



@pytest.mark.sanity
@pytest.mark.parametrize("array_mount", ["WT", "WB"])
@pytest.mark.parametrize("num_vols", [8])
def test_raid6_array_vols_data_integrity(array_fixture, array_mount, num_vols):
    """
    The purpose of this test is to create one raid6 array mounted in WT and WB. 
    Create and mount 8 volumes and utilize its full capacity. Run multiple FIO
    of File and Block IO on each Volume. And Verify the data integrify.
     
    Verification: Data Integrity on Multiple Volumes
    """
    logger.info(
        f" ==================== Test : test_raid6_array_vols_data_integrity[{array_mount}-{num_vols}] ================== "
    )
    pos = array_fixture
    try:
        num_data_disk, num_spare_disk = RAID6_MIN_DISKS, 2
        assert pos.cli.device_list()[0] == True
        if len(pos.cli.system_disks) < (num_data_disk + num_spare_disk):
            pytest.skip("Less number of system disk")

        assert single_array_data_setup(pos.data_dict, "RAID6", num_data_disk,
                                    num_spare_disk, array_mount, False) == True
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True

        assert volume_create_and_mount_multiple(pos, num_vols) == True

        assert pos.target_utils.get_subsystems_list() == True
        subs_list = pos.target_utils.ss_temp_list
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True

        fio_cmd = "fio --name=wt_verify --ioengine=libaio --rw=write --iodepth=64 --bs=128k"\
                  " --size=2gb --do_verify=1 --verify=pattern --verify_pattern=0x5678"
        assert run_fio_all_volumes(pos, fio_cmd=fio_cmd, fio_type="mix") == True

        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Test script failed due to {e}")
        pos.exit_handler(expected=False)
