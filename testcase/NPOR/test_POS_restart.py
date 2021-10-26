import pytest
import logger
import os
import json

logger = logger.get_logger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
with open("{}/../config_files/topology.json".format(dir_path)) as f:
    config_dict = json.load(f)


@pytest.mark.parametrize("io", [True, False])
def test_pos_npor_with_with_out_io(user_io, io):
    try:
        vol_list_bfr = user_io["target_setup"].cli.list_vol(array_name="POS_ARRAY1")[1]
        if io:
            dev_list = user_io["client_setup"].device_list
            fio_cmd = "fio --nme=S_W --runtime=50 --ioengine=libaio --iodepth=16 --rw=write --size=20g --bs=1m "
            user_io["client_setup"].fio_generic_runner(
                devices=dev_list, fio_data=fio_cmd
            )
        user_io["client_setup"].nvme_disconnect()
        user_io["target_setup"].cli.stop()
        user_io["target_setup"].cli.start_pos_os()
        user_io["target_setup"].cli.create_Nvmf_SS()
        user_io["target_setup"].cli.create_malloc_device()
        user_io["target_setup"].cli.scan_devs()
        user_io["target_setup"].cli.list_devs()
        user_io["target_setup"].cli.array_list()
        array_name = list(user_io["target_setup"].cli.array_dict.keys())
        user_io["target_setup"].cli.mount_array(array_name="POS_ARRAY1")
        vols = user_io["target_setup"].cli.list_vol(array_name=array_name)[1]
        if len(vols) == len(vol_list_bfr):
            logger.info("vol count matches after & before npor")
        else:
            raise Exception("volume count differs after NPOR")
        for volume in vols:
            user_io["target_setup"].mount_vol(volname=volume, array_name="POSARRAY1")
        if io:
            user_io["target_setup"].cli.create_transport()
            user_io["target_setup"].cli.add_nvmf_listner(
                mellanox_interface=config_dict["login"]["tar_mlnx_ip"]
            )
            user_io["client_setup"].nvme_connect(
                user_io["target_setup"].nqn_name, config_dict["login"]["tar_mlnx_ip"]
            )
            user_io["client_setup"].nvme_list()
            dev_list = user_io["client_setup"].nvme_list_out
            fio_cmd = "fio --name=S_W --runtime=50 --ioengine=libaio --iodepth=16 --rw=read --size=20g --bs=1m "
            user_io["client_setup"].fio_generic_runner(
                devices=dev_list, fio_data=fio_cmd
            )
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
