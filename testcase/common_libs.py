####common libs used in the Test scripts##########


def nvme_connect(pos):
    """method to do nvme connect and list"""
    assert pos.target_utils.get_subsystems_list() == True
    for ss in pos.target_utils.ss_temp_list:
        assert (
            pos.client.nvme_connect(ss, pos.target_utils.helper.ip_addr[0], "1158")
            == True
        )
    assert pos.client.nvme_list() == True
    return True, pos.client.nvme_list_out


def run_io(
    pos,
    fio_command="fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=64k --time_based --runtime=30",
):
    """method to do nvme connect, list and run block IO"""

    out = nvme_connect(pos)
    assert out[0] == True
    assert (
        pos.client.fio_generic_runner(
            out[1],
            fio_user_data=fio_command,
        )[0]
        == True
    )
    return True

def common_setup(pos,raid_type, nr_data_drives):
    
        pos.data_dict["array"]["pos_array"][0]["raid_type"] = raid_type
        pos.data_dict["array"]["pos_array"][1]["raid_type"] = raid_type
       
        pos.data_dict["array"]["pos_array"][0]["data_device"] = nr_data_drives
        pos.data_dict["array"]["pos_array"][1]["data_device"] = nr_data_drives
       
        assert pos.target_utils.bringupArray(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringupVolume(data_dict=pos.data_dict) == True
        run_io(pos)