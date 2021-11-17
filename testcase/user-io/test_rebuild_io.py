import logger
import pytest

logger = logger.get_logger(__name__)


@pytest.mark.parametrize("io", ["file", "block"])
def test_rebuild_io(user_io, io):
    try:
        flag = False
        dev_list = user_io["client"].nvme_list()[1]
        if io == "block":
            fio_cmd = "fio --name=S_W --runtime=3 --ioengine=libaio --iodepth=16 --rw=randwrite --size=1g --bs=4kb"
            assert (
                user_io["client"].fio_generic_runner(
                    devices=dev_list, fio_user_data=fio_cmd
                )
                == True
            )
        if io == "file":
            assert (
                user_io["client"].create_File_system(
                    device_list=dev_list, fs_format="xfs"
                )
                == True
            )
            dev_list = user_io["client"].nvme_list()[1]
            dev_fs_list = user_io["client"].mount_FS(device_list=dev_list)[1]
            flag = True
            fio_cmd = "fio --name=S_W  --ioengine=libaio  --iodepth=16 --rw=write --size=1g --bs=8k \
                   --verify=pattern --do_verify=0 --verify_pattern=0xa66"
            user_io["client"].fio_generic_runner(
                devices=dev_fs_list, fio_user_data=fio_cmd, IO_mode=False
            )

        data_disks = user_io["target"].cli.info_array()[4]

        user_io["target"].target_utils.device_hot_remove(device_list=[data_disks[0]])
        array_info = user_io["target"].cli.info_array()
        array_state, array_situation = array_info[2], array_info[3]
        if array_state == "BUSY" and array_situation == "REBUILDING":
            logger.info("array state is in rebuilding state")
        else:
            raise Exception("Array state is not in rebuilding state")

        user_io["target"].target_utils.check_rebuild_status()
        if io == "block":
            fio_cmd = "fio --name=S_W --runtime=180 --ioengine=libaio --iodepth=16 --rw=read --size=1g --bs=4kb"
            user_io["client"].fio_generic_runner(
                devices=dev_list, fio_user_data=fio_cmd
            )

        if io == "file":
            fio_cmd = "fio --name=S_W  --ioengine=libaio  --iodepth=16 --rw=read --size=1g --bs=8k \
                   --verify=pattern --do_verify=0 --verify_pattern=0xa66"
            user_io["client"].fio_generic_runner(
                devices=dev_fs_list, fio_user_data=fio_cmd, IO_mode=False
            )

        if io == "file":
            user_io["client"].unmount_FS(fs_mount_pt=dev_fs_list)
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        if io == "file":
            user_io["client"].unmount_FS(fs_mount_pt=dev_fs_list)
        assert 0
