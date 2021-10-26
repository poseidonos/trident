import logger, pytest

logger = logger.get_logger(__name__)


def test_pos_write_uncorr_lba(user_io):
    try:
        dev_list = user_io["client_setup"].nvme_list_out
        fio_cmd = "fio --name=test_1 --ioengine=libaio --iodepth=256 --rw=write --size=100gb --bs=4kb  --numjobs=8"
        user_io["client_setup"].fio_generic_runner(devices=dev_list, fio_data=fio_cmd)

        vols = user_io["target_setup"].cli.list_vol(array_name="POS_ARRAY1")

        read_vsamap_out = user_io["target_setup"].cli.read_vsamap_entry(
            vol_name=vols[0], rba=0, array_name="POS_ARRAY1"
        )

        vsid = read_vsamap_out["vsid"]

        stripemap_entry_out = user_io["target_setup"].cli.read_stripemap_entry(
            vsid=vsid, array_name="POS_ARRAY1"
        )[1]
        ls_id = stripemap_entry_out["lsid"]

        dev_lba_out = user_io["target_setup"].cli.translate_device_lba(
            logical_stripe_id=ls_id, logical_offset=0, array_name="POS_ARRAY1"
        )[1]
        dev_name = dev_lba_out["device name "]
        lba = user_io["target_setup"].dev_lba_out["lba "]

        user_io["target_setup"].cli.write_uncorrectable_lba(
            device_name=dev_name, lba=lba
        )
        try:
            user_io["target_setup"].cli.read_raw(dev=dev_name, lba=lba, count=10)
            assert 0
        except Exception:
            logger.info("Read raw failed")
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
