#/*
# *   BSD LICENSE
# *   Copyright (c) 2021 Samsung Electronics Corporation
# *   All rights reserved.
# *
# *   Redistribution and use in source and binary forms, with or without
# *   modification, are permitted provided that the following conditions
# *   are met:
# *
# *     * Redistributions of source code must retain the above copyright
# *       notice, this list of conditions and the following disclaimer.
# *     * Redistributions in binary form must reproduce the above copyright
# *       notice, this list of conditions and the following disclaimer in
# *       the documentation and/or other materials provided with the
# *       distribution.
# *     * Neither the name of Samsung Electronics Corporation nor the names of
# *       its contributors may be used to endorse or promote products derived
# *       from this software without specific prior written permission.
# *
# *   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# *   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# *   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# *   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# *   OWN
#/*
import logger, pytest

logger = logger.get_logger(__name__)


@pytest.mark.parametrize("io_engine", ["posixaio", "sync", "libaio"])
def test_run_block_io(user_io, io_engine):
    try:
        dev_list = user_io["client"].nvme_list()[1]

        fio_cmd = "fio --name=S_W --runtime=5 --ioengine={} --iodepth=16 --rw=write --size=1g --bs=1m ".format(
            io_engine
        )
        user_io["client"].fio_generic_runner(devices=dev_list, fio_user_data=fio_cmd)
    except Exception as e:
        logger.error("Test case failed with exception {}".format(e))
        assert 0
