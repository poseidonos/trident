import pytest, json, sys, os, time, random, codecs, re, datetime
from random import randint

import lib.logger as logger
import lib.composable.composable_core as libcore

logger = logger.get_logger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/../../testcase/config_files/system_management.json".format(dir_path)) as p:
    tc_dict = json.load(p)


def test_system_sanity_detach_attach_device_iteration_io_verify(
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
            raise AssertionError

        test_dict = tc_dict[
            "test_system_sanity_detach_attach_device_iteration_io_verify"
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

        while True:
            logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))

            assert target.cli.info_array(target.cli.array_name)[0] == True
            num_data_disks = len(
                target.cli.array_info[target.cli.array_name]["data_list"]
            )
            stripe_size_for_writing = num_data_disks * 256 * 1024
            logger.info("Lock status : release {}".format(target.cli.lock.release()))

            fio_size = stripe_size_for_writing
            pattern_data = target.cli.helper.generate_pattern(8)
            pattern_data = "0x{}".format(pattern_data)
            bs = test_dict["phase"][phase]["io"]["fio"]["bs"]
            iod = test_dict["phase"][phase]["io"]["fio"]["iodepth"]
            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio --name=fio_{} --ioengine=libaio --rw={} --offset=0"
                        " --bs=4kb --size={}  --iodepth={} --direct=1 --numjobs=1"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --verify_dump=1 --verify_fatal=1 --continue_on_error=none"
                        " --group_reporting".format(
                            "write", "write", fio_size, iod, pattern_data
                        )
                    ),
                )[0]
                == True
            )

            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio --name=fio_{} --ioengine=libaio --rw={} --offset=0"
                        " --bs=4kb --size={}  --iodepth={} --direct=1 --numjobs=1"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --continue_on_error=none"
                        " --group_reporting".format(
                            "read", "read", fio_size, iod, pattern_data
                        )
                    ),
                )[0]
                == True
            )

            logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
            assert target.cli.list_device()[0] == True
            logger.info("System Disks {}".format(target.cli.system_disks))

            assert target.cli.info_array(array_name=target.cli.array_name)[0] == True
            data_disks = target.cli.array_info[target.cli.array_name]["data_list"]
            spare_disks = target.cli.array_info[target.cli.array_name]["spare_list"]

            logger.info(
                "Data Disks {}".format(
                    target.cli.array_info[target.cli.array_name]["data_list"]
                )
            )
            logger.info(
                "Spare Disks {}".format(
                    target.cli.array_info[target.cli.array_name]["spare_list"]
                )
            )

            dev_name = random.choice(data_disks + spare_disks)
            logger.info(
                "BDF of {} is {}".format(
                    dev_name, target.cli.NVMe_BDF[dev_name]["addr"]
                )
            )
            logger.info("Lock status : release {}".format(target.cli.lock.release()))

            dev_name_list = []
            dev_name_list.append(dev_name)
            assert target.target_utils.device_hot_remove(dev_name_list) == True
            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio --name=fio_{} --ioengine=libaio --rw={} --offset=0"
                        " --bs=4kb --size={}  --iodepth={} --direct=1 --numjobs=1"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --continue_on_error=none"
                        " --group_reporting".format(
                            "read", "read", fio_size, iod, pattern_data
                        )
                    ),
                )[0]
                == True
            )

            assert target.target_utils.pci_rescan() == True

            logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
            for index in range(2):
                assert target.cli.list_device()[0] == True
                system_disks = target.cli.system_disks
                normal_disks = target.cli.normal_data_disks
                assert (
                    target.cli.info_array(array_name=target.cli.array_name)[0] == True
                )
                data_disks = target.cli.array_info[target.cli.array_name]["data_list"]
                spare_disks = target.cli.array_info[target.cli.array_name]["spare_list"]

                if len(spare_disks) == 0:
                    if len(normal_disks) < len(data_disks):
                        assert (
                            target.cli.addspare_array(
                                system_disks[0], target.cli.array_name
                            )[0]
                            == True
                        )
                    elif len(normal_disks) == len(data_disks):
                        if random.randint(0, 1):
                            assert (
                                target.cli.addspare_array(
                                    system_disks[0], target.cli.array_name
                                )[0]
                                == True
                            )
                        else:
                            logger.info("Skip add spare device")
                else:
                    logger.info("The spare device already exists")

            while True:
                assert (
                    target.cli.info_array(array_name=target.cli.array_name)[0] == True
                )
                if (
                    "normal"
                    in target.cli.array_info[target.cli.array_name]["situation"].lower()
                ):
                    break
                time.sleep(2)
            logger.info("Lock status : release {}".format(target.cli.lock.release()))

            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio --name=fio_{} --ioengine=libaio --rw={} --offset=0"
                        " --bs=4kb --size={}  --iodepth={} --direct=1 --numjobs=1"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --continue_on_error=none"
                        " --group_reporting".format(
                            "read", "read", fio_size, iod, pattern_data
                        )
                    ),
                )[0]
                == True
            )
            # logger.info("The lastest offset {} length {} eache devices write size {}".format(client._fio_offset, client._fio_length, fio_size))
            current_time = time.time()
            running_time = current_time - start_time
            if running_time >= phase_time:
                break

    except Exception as e:
        logger.error("Failed due to {}".format(e))
        logger.error(
            "Failed test case name : {}".format(sys._getframe().f_code.co_name)
        )
        logger.error("Failed test stage : {}".format(phase + 1))
        raise
