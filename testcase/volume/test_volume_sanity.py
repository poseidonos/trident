import pytest
import random
from pos import POS

import logger
logger = logger.get_logger(__name__)


def random_string(length):
    rstring = ""
    rstr_seq = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(0, length):
        if i % length == 0 and i != 0:
            rstring += "-"
        rstring += str(rstr_seq[random.randint(0, len(rstr_seq) - 1)])
    return rstring


@pytest.mark.sanity
@pytest.mark.parametrize("numvol", [1,256])
@pytest.mark.parametrize(
    "volsize", ["1mb", "1gb"]
)  # None means max size of the array/num of vols per array
def test_SanityVolume(array_fixture, numvol, volsize):
    try:

        logger.info(
            f" ============== Test : volsize {volsize} numvol {numvol}  ============="
        )
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = numvol
        pos.data_dict["volume"]["pos_volumes"][1]["num_vol"] = numvol
        pos.data_dict["array"]["num_array"] = 2
        pos.data_dict["volume"]["pos_volumes"][0]["size"] = volsize
        pos.data_dict["volume"]["pos_volumes"][1]["size"] = volsize
        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True
        # negative test Multiple invalid commands
        for nums in range(numvol):
            volname = f"tempvolpos{str(nums)}"
            assert (
                pos.cli.volume_create(
                    volumename=volname, array_name="array33", size=volsize
                )[0]
                == False
            )  # invalid array volume creation
            assert (
                pos.cli.volume_mount(volumename=volname, array_name="array1")[0]
                == False
            )  ##volume re-mount

        assert pos.cli.volume_list(array_name="array1")[0] == True
        for vol in pos.cli.vols:
            rlist = [i for i in range(10, 255)]
            newname = random_string(random.choice(rlist))
            assert pos.cli.volume_info(array_name="array1", vol_name=vol)[0] == True
            assert (
                pos.cli.volume_rename(
                    new_volname=newname, volname=vol, array_name="array1"
                )[0]
                == True
            )
            assert (
                pos.cli.volume_unmount(volumename=newname, array_name="array1")[0]
                == True
            )
            assert pos.cli.volume_info(array_name="array1", vol_name=newname)[0] == True
            assert (
                pos.cli.volume_delete(volumename=newname, array_name="array1")[0]
                == True
            )

    except Exception as e:
        logger.error(f" ======= Test FAILED due to {e} ========")
        assert 0


@pytest.mark.sanity()
def test_volumesanity257vols(array_fixture):
    array_name = "array1"
    try:
        pos = array_fixture
        pos.data_dict["volume"]["pos_volumes"][0]["num_vol"] = 256
        pos.data_dict["array"]["num_array"] = 1

        assert pos.target_utils.bringup_array(data_dict=pos.data_dict) == True
        assert pos.target_utils.bringup_volume(data_dict=pos.data_dict) == True
        # negative test
        assert (
            pos.cli.volume_create(
                volumename="invalidvol", array_name=array_name, size="1gb"
            )[0]
            == False
        )

    except Exception as e:
        logger.error(f" ======= Test FAILED due to {e} ========")
        assert 0
