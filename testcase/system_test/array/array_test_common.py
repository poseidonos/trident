import pytest
import traceback
import logger as logging

logger = logging.get_logger(__name__)


def wt_array_setup(
    pos,
    raid_type: str,
    num_data_disk: int,
    num_spare_disk: int,
    auto_create=False,
    array_index=0,
):
    try:
        data_dict = pos.data_dict
        assert pos.cli.device_list()[array_index] == True
        required_disks = num_data_disk + num_spare_disk
        if len(pos.cli.system_disks) < required_disks:
            pytest.skip(
                "Insufficient disks count {}. Required {}".format(
                    len(pos.cli.system_disks), required_disks
                )
            )
        if raid_type.upper() == "NORAID":
            raid_type = "no-raid"

        data_dict["array"]["num_array"] = 1
        pos_array = data_dict["array"]["pos_array"][0]
        array_name = pos_array["array_name"]
        pos_array["data_device"] = num_data_disk
        pos_array["spare_device"] = num_spare_disk
        pos_array["raid_type"] = raid_type
        pos_array["auto_create"] = auto_create
        pos_array["write_back"] = "false"

        assert pos.target_utils.bringup_array(data_dict=data_dict) == True
        assert pos.cli.array_info(array_name=array_name)[0] == True
    except Exception as e:
        logger.error(f"Failed to setup array due to {e}")
        traceback.print_exc()
        return False
    return True

def wt_array_volume_setup(
    pos, raid_type: str, num_data_disk: int, num_spare_disk: int, array_index=0
):
    try:
        assert wt_array_setup(pos, raid_type, num_data_disk, num_spare_disk) == True
        array_name = pos.data_dict["array"]["pos_array"][array_index]["array_name"]
        assert (
            pos.cli.volume_create("pos_vol1", array_name=array_name, size="1000gb")[0]
            == True
        )
        assert pos.target_utils.get_subsystems_list() == True
        assert pos.cli.volume_list(array_name=array_name)[0] == True
        ss_list = [ss for ss in pos.target_utils.ss_temp_list if array_name in ss]
        assert (
            pos.target_utils.mount_volume_multiple(
                array_name=array_name, volume_list=pos.cli.vols, nqn_list=ss_list
            )
            == True
        )

        for ss in pos.target_utils.ss_temp_list:
            assert (
                pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
                == True
            )
        return True
    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False


def wt_test_multi_array_setup(pos, array_list: list):
    """
    Function to setup the Multi array test environment

    array_list : List of dict of array configuration.
    """
    try:
        if pos.target_utils.helper.check_pos_exit() == True:
            assert pos.target_utils.pos_bring_up(data_dict=pos.data_dict) == True
        assert pos.cli.devel_resetmbr()[0] == True

        assert pos.cli.device_scan()[0] == True
        assert pos.cli.device_list()[0] == True
        system_disks = pos.cli.system_disks
        for array in array_list:
            array_name = array["array_name"]
            buffer_dev = array["buffer_dev"]
            raid_type = array["raid_type"]
            nr_data_drives = array["nr_data_drives"]
            write_back = array["write_back"]

            if len(system_disks) < (nr_data_drives):
                pytest.skip(
                    f"Insufficient disk count {system_disks}. Required \
                                minimum {nr_data_drives}"
                )
            data_disk_list = [system_disks.pop(0) for i in range(nr_data_drives)]

            if raid_type.upper() == "NORAID":
                raid_type = "no-raid"

            assert pos.cli.array_create(array_name=array_name,
                            write_buffer=buffer_dev, data=data_disk_list,
                            spare=[], raid_type=raid_type)[0] == True
            
            assert pos.cli.array_mount(array_name=array_name, 
                                       write_back=write_back)[0] == True
        return True
    except Exception as e:
        logger.error(f"Test setup failed due to {e}")
        traceback.print_exc()
        return False
