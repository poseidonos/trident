import logger
import pytest

logger = logger.get_logger(__name__)


@pytest.mark.parametrize("io", ["file", "block"])
def test_rebuild_io(user_io, io):
    try:
        flag = False
        devs = user_io["target_setup"].cli.dev_type["SSD"]
        dev_list = user_io["client_setup"].nvme_list_out
        if io == "block":
            fio_cmd = "fio --name=S_W --runtime=180 --ioengine=libaio --iodepth=16 --rw=randwrite --size=1g --bs=4kb"
            user_io["client_setup"].fio_generic_runner(
                devices=dev_list, fio_data=fio_cmd
            )
        if io == "file":
            user_io["client_setup"].create_File_System(
                dev_list=dev_list, format_type="xfs"
            )
            dev_fs_list = user_io["client_setup"].mount_FS(dev_list=dev_list)[1]
            flag = True
            fio_cmd = "fio --name=S_W  --ioengine=libaio  --iodepth=16 --rw=write --size=1g --bs=8k \
                   --verify=pattern --do_verify=0 --verify_pattern=0xa66"
            user_io["client_setup"].fio_generic_runner(
                devices=dev_fs_list, fio_data=fio_cmd, io_mode=False
            )

        data_disks = user_io["target_setup"].cli.get_array_info(
            array_name="POS_ARRAY1"
        )[4]

        user_io["target_setup"].target_utils.device_hot_remove(
            device_name=[data_disks[0]]
        )
        array_state = user_io["target_setup"].cli.get_array_info(
            array_name="POS_ARRAY1"
        )
        if array_state == "REBUILDING":
            logger.info("array state is in rebuilding state")
        else:
            raise Exception("Array state is not in rebuilding state")

        user_io["target_setup"].target_utils.check_rebuild_status(
            array_name="POS_ARRAY1"
        )
        if io == "block":
            fio_cmd = "fio --name=S_W --runtime=180 --ioengine=libaio --iodepth=16 --rw=read --size=1g --bs=4kb"
            user_io["client_setup"].fio_generic_runner(
                devices=dev_list, fio_data=fio_cmd
            )

        if io == "file":
            fio_cmd = "fio --name=S_W  --ioengine=libaio  --iodepth=16 --rw=read --size=1g --bs=8k \
                   --verify=pattern --do_verify=0 --verify_pattern=0xa66"
            user_io["client_setup"].fio_generic_runner(
                devices=dev_fs_list, fio_data=fio_cmd, io_mode=False
            )

        user_io["target_setup"].cli.list_devs()

        devs_1 = user_io["target_setup"].cli.dev_type["SSD"]

        spare_dev = user_io["target_setup"].cli.get_array_info(array_name="POS_ARRAY1")[
            4
        ]

        spare_dev = [dev for dev in devs_1 if dev not in devs if dev not in spare_dev]

        user_io["target_setup"].cli.add_spare_drive(
            device_name=spare_dev[0], array_name="POS_ARRAY1"
        )
        if io == "file" and flag == True:
            user_io["client_setup"].unmount_FS(unmount_dir=dev_fs_list)
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        if io == True:
            user_io["client_setup"].unmount_FS(unmount_dir=dev_fs_list)
        assert 0
