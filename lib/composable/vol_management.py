import pytest, json, sys, os, time, random, codecs, re, datetime
from random import randint

import logger as logger
import composable.composable_core as libcore

logger = logger.get_logger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/../../testcase/config_files/vol_management.json".format(dir_path)) as p:
    tc_dict = json.load(p)


def test_vol_lc_io_sanity_create_mount_io_unmount_mount_verifyio_umount_delete(
    target=None, client=None, phase=None, data_set=None, Time=None
):
    try:
        if (
            target == None
            or client == None
            or phase == None
            or data_set == None
            or Time == None
        ):
            logger.info("Mandatory params are None")
            raise AssertionError

        test_dict = tc_dict[
            "test_vol_lc_io_sanity_create_mount_io_unmount_mount_verifyio_umount_delete"
        ]

        phase_time = Time
        start_time = time.time()

        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="create",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))

        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="create",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="mount",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : release {}".format(target.cli.lock.release()))

        assert target.cli.list_volume(target.cli.array_name)[0] == True
        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="connect",
                phase=phase,
            )
            == True
        )
        time.sleep(5)

        while True:
            model_name = test_dict["phase"][0]["volume"]["create"]["basename"]
            assert client.nvme_list(model_name) == True

            write_devices = []
            read_devices = []

            write_devices = client.nvme_list_out

            write_device_count = len(write_devices)

            fio_size = "5%"
            logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
            pattern_data = target.cli.helper.generate_pattern(8)
            logger.info("Lock status : release {}".format(target.cli.lock.release()))
            pattern_data = "0x{}".format(pattern_data)
            iod = test_dict["phase"][phase]["io"]["fio"]["iodepth"]
            bs = test_dict["phase"][phase]["io"]["fio"]["bs"]
            current_time = time.time()

            assert (
                client.fio_generic_runner(
                    write_devices,
                    fio_user_data=(
                        "fio  --name=fio_write --rw=write --size={} --ioengine=libaio"
                        " --direct=1 --iodepth={} --bs={} --numjobs=1 --offset=0"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --verify_dump=1 --verify_fatal=1 --continue_on_error=none"
                        " --group_reporting".format(fio_size, iod, bs, pattern_data)
                    ),
                    json_out="test_vol_lc_io_sanity_create_mount_io_unmount_mount_verifyio_umount_delete",
                )[0]
                == True
            )

            for device in write_devices:
                assert client.nvme_flush([device]) == True

            logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
            assert (
                libcore.volume_module(
                    target=target,
                    data_set=data_set,
                    config_dict=test_dict,
                    action="unmount",
                    phase=phase,
                )
                == True
            )
            assert (
                libcore.volume_module(
                    target=target,
                    data_set=data_set,
                    config_dict=test_dict,
                    action="mount",
                    phase=phase,
                )
                == True
            )
            logger.info("Lock status : release {}".format(target.cli.lock.release()))

            model_name = test_dict["phase"][0]["volume"]["create"]["basename"]
            assert client.nvme_list(model_name) == True
            read_devices = client.nvme_list_out

            read_device_count = len(read_devices)

            if read_device_count != write_device_count:
                assert 0
            else:
                for i in range(write_device_count):
                    if read_devices[i] != write_devices[i]:
                        assert 0
            assert (
                client.fio_generic_runner(
                    read_devices,
                    fio_user_data=(
                        "fio  --name=fio_read --rw=read --size={} --ioengine=libaio"
                        " --direct=1 --iodepth={} --bs={} --numjobs=1 --offset=0"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --continue_on_error=none"
                        " --group_reporting".format(fio_size, iod, bs, pattern_data)
                    ),
                    json_out="test_vol_lc_io_sanity_create_mount_io_unmount_mount_verifyio_umount_delete",
                )[0]
                == True
            )
            logger.info(
                "End Fio Read Test"
                " test_vol_lc_io_sanity_create_mount_io_unmount_mount_verifyio_umount_delete"
            )
            current_time = time.time()
            running_time = current_time - start_time
            if running_time >= phase_time:
                break

        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="disconnect",
                phase=phase,
            )
            == True
        )

        logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="unmount",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="delete",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="delete",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : release {}".format(target.cli.lock.release()))
    except Exception as e:
        logger.error("Failed due to {}".format(e))
        logger.error(
            "Failed test case name : {}".format(sys._getframe().f_code.co_name)
        )
        logger.error("Failed test stage : {}".format(phase + 1))
        raise


def test_vol_lc_stress_unmount_delete_create_mount_io(
    target=None, client=None, phase=None, data_set=None, Time=None
):
    try:
        if target == None or client == None or phase == None or data_set == None:
            raise AssertionError

        test_dict = tc_dict["test_vol_lc_stress_unmount_delete_create_mount_io"]

        phase_time = Time
        start_time = time.time()

        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="create",
                phase=phase,
            )
            == True
        )

        logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))

        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="unmount",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="delete",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="create",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="mount",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : release {}".format(target.cli.lock.release()))
        assert target.cli.list_volume(target.cli.array_name)[0] == True
        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="connect",
                phase=phase,
            )
            == True
        )
        time.sleep(5)
        model_name = test_dict["phase"][0]["volume"]["create"]["basename"]
        assert client.nvme_list(model_name) == True
        fio_device = client.nvme_list_out

        current_time = time.time()
        fio_time = phase_time - (current_time - start_time)
        if fio_time < 5:
            fio_time = 10

        assert (
            client.fio_generic_runner(
                devices=fio_device,
                fio_user_data=(
                    "fio  --name=fio_write --rw={} --size={} --fsync=1"
                    " --ioengine=libaio --iodepth={} --bs={} --numjobs=1 --time_based "
                    " --runtime={} --group_reporting".format(
                        test_dict["phase"][phase]["io"]["fio"]["rw"],
                        test_dict["phase"][phase]["io"]["fio"]["size"],
                        test_dict["phase"][phase]["io"]["fio"]["iodepth"],
                        test_dict["phase"][phase]["io"]["fio"]["bs"],
                        fio_time,
                    )
                ),
                json_out="test_vol_lc_stress_unmount_delete_create_mount_io",
            )[0]
            == True
        )
    except Exception as e:
        logger.error("Failed due to {}".format(e))
        logger.error(
            "Failed test case name : {}".format(sys._getframe().f_code.co_name)
        )
        logger.error("Failed test stage : {}".format(phase + 1))
        raise


def test_vol_lc_io_sanity_create_mount_verifyqos_unmount_delete(
    target=None, client=None, phase=None, data_set=None, Time=None
):
    try:
        if target == None or client == None or phase == None or data_set == None:
            raise AssertionError

        test_dict = tc_dict[
            "test_vol_lc_io_sanity_create_mount_verifyqos_unmount_delete"
        ]

        phase_time = Time
        start_time = time.time()

        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="create",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="create",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="mount",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : release {}".format(target.cli.lock.release()))
        assert target.cli.list_volume(target.cli.array_name)[0] == True
        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="connect",
                phase=phase,
            )
            == True
        )
        time.sleep(5)
        model_name = test_dict["phase"][0]["volume"]["create"]["basename"]
        assert client.nvme_list(model_name) == True
        fio_device = client.nvme_list_out

        current_time = time.time()
        fio_time = phase_time - (current_time - start_time)
        if fio_time < 5:
            fio_time = 10

        while True:
            io_type_list = ["write", "read"]
            io_type_data = random.choice(io_type_list)
            logger.info("fio time : {} , io type : {}".format(fio_time, io_type_data))
            fio_out = {}
            ret, fio_out = client.fio_generic_runner(
                devices=fio_device,
                fio_user_data=(
                    "fio  --name=fio_{} --rw={} --size={} --ioengine=libaio"
                    " --iodepth={} --bs={} --numjobs=1 --direct=1 --group_reporting".format(
                        io_type_data,
                        io_type_data,
                        test_dict["phase"][phase]["io"]["fio"]["size"],
                        test_dict["phase"][phase]["io"]["fio"]["iodepth"],
                        test_dict["phase"][phase]["io"]["fio"]["bs"],
                    )
                ),
                json_out="test_vol_lc_io_sanity_create_mount_verifyqos_unmount_delete",
            )

            assert ret == True

            fio_bw_write = client.fio_par_out["write"]["bw"]
            fio_iops_write = client.fio_par_out["write"]["iops"]
            fio_bw_read = client.fio_par_out["read"]["bw"]
            fio_iops_read = client.fio_par_out["read"]["iops"]

            logger.info(
                "QoS check / write bw {}, iops {} / read bw {}, iops {}".format(
                    fio_bw_write, fio_iops_write, fio_bw_read, fio_iops_read
                )
            )

            ###############################################
            ##In here, need to verify QoS for each VOLUME##
            ###############################################

            # Use fio parser
            logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
            assert (
                libcore.volume_module(
                    target=target,
                    data_set=data_set,
                    config_dict=test_dict,
                    action="update",
                    phase=phase,
                )
                == True
            )
            logger.info("Lock status : release {}".format(target.cli.lock.release()))
            current_time = time.time()
            running_time = current_time - start_time
            if running_time >= phase_time:
                break

        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="disconnect",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="unmount",
                phase=phase,
            )
            == True
        )
        assert (
            libcore.volume_module(
                target=target,
                data_set=data_set,
                config_dict=test_dict,
                action="delete",
                phase=phase,
            )
            == True
        )
        logger.info("Lock status : release {}".format(target.cli.lock.release()))
        assert (
            libcore.subsystem_module(
                target=target,
                client=client,
                data_set=data_set,
                config_dict=test_dict,
                action="delete",
                phase=phase,
            )
            == True
        )
    except Exception as e:
        logger.error("Failed due to {}".format(e))
        logger.error(
            "Failed test case name : {}".format(sys._getframe().f_code.co_name)
        )
        logger.error("Failed test stage : {}".format(phase + 1))
        raise
