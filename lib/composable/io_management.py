import pytest, json, sys, os, time, random, codecs, re, datetime
from random import randint

import logger as logger
import composable.composable_core as libcore

# sys.path.insert(0, "/root/poseidon/commit2505/trident")
logger = logger.get_logger(__name__)
dir_path = os.path.dirname(os.path.realpath(__file__))

with open("{}/../../testcase/config_files/io_management.json".format(dir_path)) as p:
    tc_dict = json.load(p)


def test_io_sanity_iteration_io_verify_random_pattern(
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

        test_dict = tc_dict["test_io_sanity_iteration_io_verify_random_pattern"]

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
            fio_size = random.choice(["5%", "10%"])
            pattern_data = target.cli.helper.generate_pattern(8)
            pattern_data = "0x{}".format(pattern_data)
            bs = test_dict["phase"][phase]["io"]["fio"]["bs"]
            iod = test_dict["phase"][phase]["io"]["fio"]["iodepth"]
            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio  --name=fio_write --rw=write --size={} --ioengine=libaio"
                        " --direct=1 --iodepth={} --bs={} --numjobs=1 --offset=0"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --verify_dump=1 --verify_fatal=1 --continue_on_error=none"
                        " --group_reporting".format(fio_size, iod, bs, pattern_data)
                    ),
                    json_out="test_io_sanity_iteration_io_verify_random_pattern",
                )[0]
                == True
            )

            # logger.info("The lastest offset {} length {} eache devices write size {}".format(client._fio_offset, client._fio_length, fio_size))
            current_time = time.time()
            running_time = current_time - start_time
            if running_time >= phase_time:
                break

            bs = test_dict["phase"][phase]["io"]["fio"]["bs"]
            iod = test_dict["phase"][phase]["io"]["fio"]["iodepth"]

            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio  --name=fio_read --rw=read --size={} --ioengine=libaio"
                        " --direct=1 --iodepth={} --bs={} --numjobs=1 --offset=0"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --continue_on_error=none"
                        " --group_reporting".format(fio_size, iod, bs, pattern_data)
                    ),
                    json_out="test_io_sanity_iteration_io_verify_random_pattern",
                )[0]
                == True
            )

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


def test_io_sanity_set_get_threashold_io_gc(
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

        test_dict = tc_dict["test_io_sanity_set_get_threashold_io_gc"]

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
            assert (
                target.cli.wbt_get_gc_status(array_name=target.cli.array_name)[0]
                == True
            )
            assert (
                target.cli.wbt_get_gc_threshold(array_name=target.cli.array_name)[0]
                == True
            )

            if target.cli.free_segments > 5:
                normal_threshold = random.randint(4, int(target.cli.free_segments))
                urgent_threshold = random.randint(2, int(target.cli.gc_normal) - 1)
                if normal_threshold < urgent_threshold:
                    normal_threshold, urgent_threshold = (
                        urgent_threshold,
                        normal_threshold,
                    )
                logger.info(
                    "Set normal threshold {}, urgent threshold {}".format(
                        normal_threshold, urgent_threshold
                    )
                )
                assert (
                    target.cli.wbt_set_gc_threshold(
                        array_name=target.cli.array_name,
                        normal=normal_threshold,
                        urgent=urgent_threshold,
                    )[0]
                    == True
                )
                assert (
                    target.cli.wbt_get_gc_threshold(array_name=target.cli.array_name)[0]
                    == True
                )

            assert target.cli.info_array(target.cli.array_name)[0] == True
            num_data_disks = len(
                target.cli.array_info[target.cli.array_name]["data_list"]
            )
            stripe_size_for_writing = num_data_disks * 256 * 1024
            logger.info("Lock status : release {}".format(target.cli.lock.release()))

            fio_size = stripe_size_for_writing
            logger.info("Lock status : acquire {}".format(target.cli.lock.acquire()))
            pattern_data = target.cli.helper.generate_pattern(8)
            logger.info("Lock status : release {}".format(target.cli.lock.release()))
            pattern_data = "0x{}".format(pattern_data)
            bs = test_dict["phase"][phase]["io"]["fio"]["bs"]
            iod = test_dict["phase"][phase]["io"]["fio"]["iodepth"]
            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio  --name=fio_write --rw=write --size={} --ioengine=libaio"
                        " --direct=1 --iodepth={} --bs={} --numjobs=1 --offset=0"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --verify_dump=1 --verify_fatal=1 --continue_on_error=none"
                        " --group_reporting".format(fio_size, iod, bs, pattern_data)
                    ),
                    json_out="test_io_sanity_set_get_threashold_io_gc",
                )[0]
                == True
            )

            # logger.info("The lastest offset {} length {} eache devices write size {}".format(client._fio_offset, client._fio_length, fio_size))
            current_time = time.time()
            running_time = current_time - start_time
            if running_time >= phase_time:
                break

            bs = test_dict["phase"][phase]["io"]["fio"]["bs"]
            iod = test_dict["phase"][phase]["io"]["fio"]["iodepth"]

            assert (
                client.fio_generic_runner(
                    devices=fio_device,
                    fio_user_data=(
                        "fio  --name=fio_read --rw=read --size={} --ioengine=libaio"
                        " --direct=1 --iodepth={} --bs={} --numjobs=1 --offset=0"
                        " --verify=pattern --verify_pattern={} --do_verify=1"
                        " --continue_on_error=none"
                        " --group_reporting".format(fio_size, iod, bs, pattern_data)
                    ),
                    json_out="test_io_sanity_set_get_threashold_io_gc",
                )[0]
                == True
            )

            current_time = time.time()
            running_time = current_time - start_time
            if running_time >= phase_time:
                break

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
        logger.info("Lock status : release {}".format(target.cli.lock.release()))
    except Exception as e:
        logger.error("Failed due to {}".format(e))
        logger.error(
            "Failed test case name : {}".format(sys._getframe().f_code.co_name)
        )
        logger.error("Failed test stage : {}".format(phase + 1))
        raise
