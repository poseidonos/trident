from collections import defaultdict
import time, random, sys
from random import randint
import logger as logger

# sys.path.insert(0, "/root/poseidon/trident_dev/trident")
logger = logger.get_logger(__name__)


class _Data:
    def __init__(self, seed):
        self.vols = defaultdict(list)
        self.subsystem = defaultdict(list)
        self.seed = seed

    class _Vol:
        def __init__(self, name, size, maxiops, maxbw):
            self.name = name
            self.size = size
            self.maxiops = maxiops
            self.maxbw = maxbw
            self.attachNqn = None
            self.state = "unmount"

    class _Subsystem:
        def __init__(self, name, serial, model):
            self.name = name
            self.serial = serial
            self.model = model
            self.address = None
            self.port = None
            self.transport = None
            self.state = "disconnect"

    def add_volume(self, basename, maxiops=0, maxbw=0, size=21474836480):
        if not basename:
            raise AssertionError
        if not self.vols.get(basename):
            start = 0
        else:
            last_vol = self.vols[basename][len(self.vols[basename]) - 1].name
            start = int(last_vol.split("_")[-1]) + 1
        name = basename + "_" + str(self.seed) + "_" + str(start)
        tVol = self._Vol(name=name, size=size, maxiops=maxiops, maxbw=maxbw)
        self.vols[basename].append(tVol)
        return name

    def remove_volume(self, basename):
        if not basename:
            raise AssertionError
        if not self.vols.get(basename):
            raise AssertionError
        tVol = self.vols[basename][0]
        if tVol.state == "mount":
            raise AssertionError
        del self.vols[basename][0]
        return tVol.name

    def get_volume(self, basename, number):
        if not basename or not number:
            raise AssertionError
        if not self.vols.get(basename):
            raise AssertionError
        vol_list = []
        for idx in range(int(number)):
            tVol = self.vols[basename][idx]
            vol_list.append(tVol.name)
        return vol_list

    def get_all_volumes(self):
        vol_list = []
        for vol_key in self.vols:
            for vol_entry in self.vols[vol_key]:
                vol_list.append(vol_entry)
        return vol_list

    def set_volume_state(self, basename, number, nqnname=None, state="unmount"):
        if not basename or not number:
            raise AssertionError
        if not self.vols.get(basename):
            raise AssertionError
        for idx in range(int(number)):
            self.vols[basename][idx].state = state
            self.vols[basename][idx].attachNqn = nqnname

    def add_subsystem(self, basename, serial="IBOF00000000000001", model="IBOF_VOLUME"):
        if not basename:
            raise AssertionError
        if not self.subsystem.get(basename):
            start = 0
        else:
            last_subsystem = self.subsystem[basename][
                len(self.subsystem[basename]) - 1
            ].name
            start = int(last_subsystem.split("_")[-1]) + 1
        name = basename + "_" + str(self.seed) + "_" + str(start)
        tSubsystem = self._Subsystem(name=name, serial=serial, model=model)
        self.subsystem[basename].append(tSubsystem)
        return name

    def remove_subsystem(self, basename):
        if not basename:
            raise AssertionError
        if not self.subsystem.get(basename):
            raise AssertionError
        tSubsystem = self.subsystem[basename][0]
        del self.subsystem[basename][0]
        return tSubsystem.name

    def get_subsystem(self, basename):
        if not basename:
            raise AssertionError
        if not self.subsystem.get(basename):
            raise AssertionError
        return self.subsystem[basename][0].name

    def get_all_subsystem(self):
        tSubsystem = []
        logger.info(" Inside get_all_subsystem ")
        for subsystem_dict in self.subsystem:
            logger.info("subsystem_dict {}".format(subsystem_dict))
            for subsystem in self.subsystem[subsystem_dict]:
                logger.info("subsystem {}".format(subsystem))
                tSubsystem.append(subsystem)
        return tSubsystem

    def set_subsystem_state(self, basename, state="disconnect"):
        if not basename:
            raise AssertionError
        if not self.subsystem.get(basename):
            raise AssertionError
        self.subsystem[basename][-1].state = state

    def set_all_subsystem_state(self, state):
        for subsystem_dict in self.subsystem:
            for subsystem in subsystem_dict:
                subsystem.state = state


def subsystem_module(target, client, data_set, config_dict, action, phase=None):
    try:
        if not action in ("create", "delete", "connect", "disconnect", "get_name"):
            raise AssertionError
        if phase == None:
            raise AssertionError

        def create(basename):
            model_number = config_dict["phase"][0]["volume"]["create"]["basename"]
            nqn_name = data_set.add_subsystem(basename, model=model_number)
            # nqn_name = data_set.add_subsystem(basename, model=data_set.seed)
            # model_number = "{}{}".format("POS_VOLUME", data_set.seed)
            # ip = target.get_transport_protocol_ip()
            # ip = target.ibof_obj.ssh_obj.hostname
            ip = target.target_utils.helper.get_mellanox_interface_ip()[1][0]
            # transport_protocol = target.params["transport_protocol"]
            port = "1158"
            data_set.subsystem[basename][-1].address = ip
            data_set.subsystem[basename][-1].port = port
            # data_set.subsystem[basename][-1].transport = transport_protocol
            assert (
                target.cli.subsystem_create(
                    nqn_name=nqn_name, ns_count="256", model_name=model_number, serial_number = "POS000000000001"
                )[0]
                == True
            )
            assert target.target_utils.get_subsystems_list() == True
            assert (
                target.cli.subsystem_add_listner(
                    nqn_name=nqn_name, mellanox_interface=ip, port=port
                )[0]
                == True
            )

        def delete(basename):
            nqn_name = data_set.remove_subsystem(basename)
            assert target.cli.subsystem_delete(nqn_name=nqn_name)[0] == True

        def connect(basename):
            nqn_name = data_set.get_subsystem(basename)
            ip = data_set.subsystem[basename][-1].address
            # transport_protocol = data_set.subsystem[basename][-1].transport
            port = data_set.subsystem[basename][-1].port
            assert (
                client.nvme_connect(nqn_name=nqn_name, mellanox_switch_ip=ip, port=port)
                == True
            )
            data_set.set_subsystem_state(basename=basename, state="connect")

        def disconnect(basename):
            nqn_name = data_set.get_subsystem(basename)
            logger.info("Disonnecting nqn {}".format(nqn_name))
            assert client.nvme_disconnect(nqn=nqn_name) == True
            data_set.set_subsystem_state(basename=basename, state="disconnect")

        def get_name(basename):
            nqn_name = data_set.get_subsystem(basename)
            return nqn_name

        if action == "get_name":
            if not config_dict["phase"][phase]["nvmf_subsystem"]["connect"]["valid"]:
                return False
            subsystem_name = config_dict["phase"][phase]["nvmf_subsystem"]["connect"][
                "basename"
            ].split(",")
            subnqn_list = []
            for basename in subsystem_name:
                subnqn_list.append(get_name(basename))
            return subnqn_list
        else:
            if not config_dict["phase"][phase]["nvmf_subsystem"][action]["valid"]:
                return True
            subsystem_name = config_dict["phase"][phase]["nvmf_subsystem"][action][
                "basename"
            ].split(",")
            for basename in subsystem_name:
                if action == "create":
                    create(basename)
                elif action == "delete":
                    delete(basename)
                elif action == "connect":
                    connect(basename)
                elif action == "disconnect":
                    disconnect(basename)
                else:
                    raise AssertionError
        return True
    except Exception as e:
        logger.error("{} Failed {}".format(__name__, e))
        return False


def volume_module(target, data_set, config_dict, action, phase=None):
    try:
        logger.info(
            "Action={}, phase={}, valid_action? {}".format(
                action, phase, config_dict["phase"][phase]["volume"][action]["valid"]
            )
        )
        if not action in ("unmount", "delete", "create", "mount", "update"):
            raise AssertionError
        if phase == None:
            raise AssertionError
        if not config_dict["phase"][phase]["volume"][action]["valid"]:
            return True

        assert target.cli.list_array()[0] == True
        array_list = list(target.cli.array_dict.keys())
        array_name = array_list[0]

        def create(basename, number):
            maxiops = config_dict["phase"][phase]["volume"]["create"]["maxiops"]
            maxbw = config_dict["phase"][phase]["volume"]["create"]["maxbw"]
            size = config_dict["phase"][phase]["volume"]["create"]["size"]
            for idx in range(int(number)):
                vol = data_set.add_volume(basename)
                assert (
                    target.cli.volume_create(
                        volumename=vol,
                        size=size,
                        array_name=array_name,
                        iops=maxiops,
                        bw=maxbw,
                    )[0]
                    == True
                )

        def delete(basename, number):
            for idx in range(int(number)):
                vol = data_set.remove_volume(basename)
                assert (
                    target.cli.volume_delete(volumename=vol, array_name=array_name)[0]
                    == True
                )

        def mount(basename, number, subsystem):
            nqnname = data_set.get_subsystem(subsystem)
            vol_list = data_set.get_volume(basename, number)
            for vol in vol_list:
                assert (
                    target.cli.volume_mount(
                        volumename=vol, array_name=array_name, nqn=nqnname
                    )[0]
                    == True
                )
            data_set.set_volume_state(
                basename=basename, number=number, nqnname=nqnname, state="mount"
            )

        def unmount(basename, number):
            vol_list = data_set.get_volume(basename, number)
            for vol in vol_list:
                assert (
                    target.cli.volume_unmount(volumename=vol, array_name=array_name)[0]
                    == True
                )
            data_set.set_volume_state(basename=basename, number=number, state="unmount")

        def update(basename, number):
            vol_list = data_set.get_volume(basename, number)
            for vol in vol_list:
                # both min and max are decided by SRS(v0.10.1)
                iops = random.randint(10, 18446744073709551)
                bw = random.randint(10, 17592186044415)
                assert (
                    target.cli.qos_create_volume_policy(
                        volumename=vol,
                        arrayname=array_name,
                        maxiops=iops,
                        maxbw=bw,
                        miniops=0,
                        minbw=0,
                    )[0]
                    == True
                )

        vol_basename = config_dict["phase"][phase]["volume"][action]["basename"].split(
            ","
        )
        vol_number = config_dict["phase"][phase]["volume"][action]["number"].split(",")
        for idx, (basename, number) in enumerate(zip(vol_basename, vol_number)):
            if action == "mount":
                subsystem = config_dict["phase"][phase]["volume"]["mount"][
                    "nqnbasename"
                ].split(",")[idx]
                mount(basename, number, subsystem)
            elif action == "unmount":
                unmount(basename, number)
            elif action == "create":
                create(basename, number)
            elif action == "delete":
                delete(basename, number)
            elif action == "update":
                update(basename, number)
            else:
                raise AssertionError

    except Exception as e:
        logger.error("{} Failed {}".format(__name__, e))
        return False
    return True


def npor_recover(target, data_set):
    try:
        assert target.target_utils.npor_and_save_state() == True
        assert target.cli.subsystem_create_transport()[0] == True

        logger.info("Post NPOR get_all_subsystem")

        total_subsystem = data_set.get_all_subsystem()

        logger.info("total_subsystem {}".format(total_subsystem))

        for subsystem in total_subsystem:
            name = subsystem.name
            serial = subsystem.serial
            model = subsystem.model
            ip = subsystem.address
            port = subsystem.port
            assert (
                target.cli.subsystem_create(
                    nqn_name=name, ns_count="256", model_name=model, serial_number = "POS000000000001"
                )[0]
                == True
            )
            assert (
                target.cli.subsystem_add_listner(
                    nqn_name=name, mellanox_interface=ip, port=port
                )[0]
                == True
            )

        assert target.cli.list_array()[0] == True
        array_list = list(target.cli.array_dict.keys())
        array_name = array_list[0]

        vol_list = data_set.get_all_volumes()
        for vol in vol_list:
            nqn_name = vol.attachNqn
            if nqn_name == None:
                assert 0
            assert (
                target.cli.volume_mount(
                    volumename=vol.name, array_name=array_name, nqn=nqn_name
                )[0]
                == True
            )
        return True

    except Exception as e:
        logger.error("{} Failed {}".format(__name__, e))
        return False

    time.sleep(10)
