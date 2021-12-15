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
import logger
import random
import pytest

logger = logger.get_logger(__name__)


def test_create_vol(vol_fixture):
    pass


def test_vol_list(vol_fixture):
    try:
        pos = vol_fixture
        assert pos.cli.list_volume(array_name="POS_ARRAY1")[0] == True
    except Exception as e:
        logger.error("Testcase failed with exception {}".format(e))
        assert 0


def test_vol_mount_unmount_delete(vol_fixture):
    try:
        vols = []
        out = vol_fixture.cli.list_volume(array_name="POS_ARRAY1")
        for vol_data in out[2]:
            assert vol_fixture.cli.unmount_volume(vol_data, "POS_ARRAY1")[0] == True
            assert vol_fixture.cli.delete_volume(vol_data, "POS_ARRAY1")[0] == True
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0


@pytest.mark.parametrize("length", [3, 63, 255])
def test_vol_create_diff_chars_length(mount_array, length):
    try:
        vol_name = "a" * length
        assert (
            mount_array.cli.create_volume(vol_name, "1gb", array_name="POS_ARRAY1")[0]
            == True
        )
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0


@pytest.mark.parametrize("length", [1, 256])
def test_vol_create_diff_chars_length_invalid_length(mount_array, length):
    try:
        vol_name = "a" * length
        assert (
            mount_array.cli.create_volume(vol_name, "1gb", array_name="POS_ARRAY1")[0]
            == False
        )
    except Exception as e:
        logger.error("Testcase failed with exception {}".format(e))
        assert 0


@pytest.mark.parametrize("length", [3, 63, 255])
def test_rename_vol_with_diff_char_length(mount_array, length):
    try:
        vol_name = "test_rename_" * length
        assert (
            mount_array.cli.create_volume("temp_vol", "1gb", array_name="POS_ARRAY1")[0]
            == True
        )
        mount_array.cli.rename_volume(
            new_volname=vol_name, volname="temp_vol", array_name="POS_ARRAY1"
        )
    except Exception as e:
        logger.error("Testcase failed with exception {}".format(e))
        assert 0


@pytest.mark.parametrize("length", [1, 256])
def test_rename_vol_with_diff_char_length_invalid(mount_array, length):
    try:
        volume_name = "test_rename_"
        mount_array.cli.create_volume(volume_name, "1gb", array_name="POS_ARRAY1")
        new_volume_name = "v" * length
        assert (
            mount_array.cli.rename_volume(
                new_volname=new_volume_name,
                volname=volume_name,
                array_name="POS_ARRAY1",
            )[0]
            == False
        )
    except Exception as e:
        logger.error("testcase failed with exception {}".format(e))
        assert 0


def test_create_max_vol(mount_array):
    try:
        assert (
            mount_array.target_utils.create_mount_multiple(
                num_vols=256, array_name="POS_ARRAY1"
            )
            == True
        )
    except Exception as e:
        logger.error("test case failed with exception {}".format(e))
        assert 0
