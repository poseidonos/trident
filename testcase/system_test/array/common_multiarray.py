import random
import time
from unittest import expectedFailure
import logger

logger = logger.get_logger(__name__)


def volume_create_and_mount_multiple(
    pos: object,
    num_volumes: int,
    vol_utilize=100,
    array_list=None,
    mount_vols=True,
    subs_list=[],
):
    try:
        if not array_list:
            assert pos.cli.list_array()[0] == True
            array_list = list(pos.cli.array_dict.keys())

        if not subs_list:
            assert pos.cli.subsystem_list()[0] == True
            subs_list = pos.target_utils.ss_temp_list

        for array_name in array_list:
            assert pos.cli.array_info(array_name=array_name)[0] == True

            array_cap = int(pos.cli.array_info[array_name]["size"])
            vol_size = array_cap * (vol_utilize / 100) / num_volumes
            vol_size = f"{int(vol_size / (1024 * 1024))}mb"  # Size in mb

            exp_res = True
            if num_volumes > 256 or vol_utilize > 100:
                exp_res = False

            vol_name_pre = f"{array_name}_POS_Vol"
            assert (
                pos.target_utils.create_volume_multiple(
                    array_name, num_volumes, vol_name=vol_name_pre, size=vol_size
                )
                == exp_res
            )

            assert pos.cli.volume_list(array_name=array_name)[0] == True
            if mount_vols:
                ss_list = [ss for ss in subs_list if array_name in ss]
                assert (
                    pos.target_utils.mount_volume_multiple(
                        array_name, pos.cli.vols, ss_list[0]
                    )
                    == True
                )
    except Exception as e:
        logger.error(f"Create and Mount Volume Failed due to {e}")
        return False
    return True


def volume_create_and_mount_multiple_with_io(pos, num_volumes, fio_cmd=None):
    try:
        assert volume_create_and_mount_multiple(pos, num_volumes) == True
        assert pos.cli.subsystem_list()[0] == True
        subs_list = pos.target_utils.ss_temp_list
        ip_addr = pos.target_utils.helper.ip_addr[0]
        for nqn in subs_list:
            assert pos.client.nvme_connect(nqn, ip_addr, "1158") == True
        assert pos.client.nvme_list() == True
        dev_list = pos.client.nvme_list_out
        if fio_cmd is not None:
            fio_user_data = fio_cmd
        else:
            fio_cmd = "fio --name=sequential_write --ioengine=libaio --rw=randwrite --iodepth=64 --direct=1 --numjobs=1 --bs=4k --time_based --runtime=120"
            fio_user_data = fio_cmd

        assert (
            pos.client.fio_generic_runner(pos.client.nvme_list_out, fio_user_data)[0]
            == True
        )
        logger.info(
            " ============================= Test ENDs ======================================"
        )
    except Exception as e:
        logger.error(f"Create and Mount Volume Failed due to {e}")
        return False
    return True
