import logger

logger = logger.get_logger(__name__)
class pos_management():
    def setup_env_pos(self):
        """
        Method runs setup_env.sh from scripts
        """
        ret = self.pos_obj.setup_env_pos()
        if ret == False:
           self.status = {'ret_code':'fail','message': "Failed to run setup_env"}
        else:
           self.status = {'ret_code':'pass','message': "Successfully ran setup env"}

    def start_pos_os(self):
        """
        methods starts pos process
        """
        ret = self.pos_obj.start_pos_os()
        if ret == False:
           self.status = {'ret_code':'fail','message': "failed to start pos os"}
        else:
           self.status = {'ret_code':'pass','message': "Successfully pos os is started"}

    def get_pos_info_system(self):
        """
        method to get_pos_system info
        """
        out = self.pos_obj.get_pos_info_system()
        if out[0] is True:
           self.status = {'ret_code': 'pass', 'message': 'get_pos_system_infopassed'}
        else:
           self.status = {'ret_code': 'fail', 'message': ' failed to get system info details'}
        self.pos_info = out[1]

    def pos_version(self):
        """
        method to get cli version
        """
        out = self.pos_obj.pos_version()
        if out[0] is True:
           self.status = {'ret_code': 'pass', 'message': 'Successfully fetched cli version details'}
        else:
           self.status = {'ret_code': 'fail', 'message': ' failed to get cli version details'}
        self.pos_version = out[1]

    def stop(self, grace_shutdown = True):
        """
        Method to kill pos os
        """
        ret = self.pos_obj.stop_pos_os(grace_shutdown = grace_shutdown)
        if ret == False:
           self.status = {'ret_code':'fail','message': "failed to stop pos os"}
        else:
           self.status = {'ret_code':'pass','message': "Successfully pos os was stopped"}

class unvme_management(pos_management):
    def create_malloc_device(self, uram_name = 'uram0', buffer_size = '4608', strip_size = '512'):
        """
        method to create malloc devices
        """
        ret = self.pos_obj.construct_melloc_device(uram_name = uram_name, bufer_size=buffer_size, strip_size=strip_size)
        if ret == False:
           self.status = {'ret_code' :"fail", 'message' : "failed to create  malloc device"}
        else:
           self.status = {'ret_code' :"pass", 'message' : "Successfully created malloc device"}

    def scan_devs(self):
        """
        Method to scan_devs
        """
        ret = self.pos_obj.scan_dev()
        if ret[0] == False:
           self.status = {'ret_code' :"fail", 'message' : "failed to scan devices"}
        else:
           self.status = {'ret_code' :"pass", 'message' : "Successfully devices were scaned"}

    def list_devs(self):
        """
        Method to list_devices
        """
        self.ret, self.out, self.dev, self.device_bdf, self.dev_type  = self.pos_obj.list_dev()
        if self.ret == True:
           self.status = {'ret_code' :"pass", 'message' : "Successfully devices were listed"}
           if (len(self.dev_type['NVRAM'])) != 0 and (len(self.dev_type['SSD'])) != 0:
              self.NVMe_devices = self.dev_type['SSD']
              self.RAM_disks = self.dev_type['NVRAM']
           else:
              self.NVMe_devices = []
              self.RAM_disks = []
        else:
           self.status = {'ret_code' :"fail", 'message' : "failed to list devices"}

    def setup_resetup(self):
        """
        Method to bring back the nvme devices from user mode to kernel mode
        """
        resetup_status = self.pos_obj.setup_reset()
        if resetup_status == False:
           self.status = {'message':"failed to move drives from user space to kernel space",'ret_code':"fail"}
        else:
           self.status = {'message':"Successfuly moved drives from user space to kernel space",'ret_code':"pass"}

class array_management(unvme_management):
    def array_reset(self):
        """
        Method to do array reset
        """
        arr_reset_status = self.pos_obj.array_reset()
        if arr_reset_status[0] == False:
           self.status = {'message':"failed to do mbr reset",'ret_code':"fail"}
        else:
           self.status = {'message':"Successfuly mbr reset is done",'ret_code':"pass"}
        self.arr_reset_out = arr_reset_status[1]

    def create_array(self, array_name, num_ds = None, num_wb = None, spare_count = None, buffer_list = None, data_list = None, spare_list = None, raid_type = "RAID5"):
        """
        Method to create the array
        params :
             numds : number of data drive
             numwb : number of write buff
             spare_count : number of spare drives
        """
        if num_ds is None:
           num_ds = self.params['num_datastorage']

        if num_wb is None:
           num_wb = self.params['num_writebuff']

        if len(self.NVMe_devices) < num_ds:
           self.status = {'ret_code' :"fail", 'message': "Not enough NVMe disks available for datastorage"}
           return

        if len(self.RAM_disks) <  num_wb:
           self.status = {'ret_code' :"fail", 'message': "Not enough NVMe disks available for writebuffer"}
           return

        spare_available = len(self.NVMe_devices) - num_ds
        if spare_count is None:
           num_spare = self.params['num_spare_devs']
        elif isinstance(spare_count, int) is True:
           num_spare = spare_count

        if num_spare > spare_available:
           self.status = {'ret_code' :"fail", 'message': "given number of spare disks are not avaliable"}
           return
        if buffer_list is not None:
           self.RAM_disks = buffer_list
        if data_list is not None:
           self.NVMe_devices = data_list
        if spare_list is  None:
            spare_dev = ','.join(self.NVMe_devices[-num_spare:])
        else:
            spare_dev = ','.join(spare_list[-num_spare:])
        buffer_dev = ','.join(self.RAM_disks[0:num_wb])
        storage_dev = ','.join(self.NVMe_devices[0:num_ds])
        self.array_reset()
        if self.status['ret_code'] is "fail":
           return

        if num_spare == 0:
           mnt_status = self.pos_obj.create_array(write_buffer = buffer_dev, datastorage = storage_dev,raid_type = raid_type,array_name = array_name)
        else:
           mnt_status = self.pos_obj.create_array(write_buffer = buffer_dev, datastorage = storage_dev, spare = spare_dev, raid_type = raid_type,array_name = array_name)

        if mnt_status[0] == True:
           self.status = {'ret_code' :"pass", 'message': "Successfully array is created"}
        else:
           self.status = {'ret_code' :"fail", 'message': "failed to create array"}
        self.create_array_out = mnt_status[1]

    def mount_array(self, array_name):
        """
        Method to Mount pos array
        """
        mnt_status = self.pos_obj.mount_array(array_name = array_name)
        if mnt_status[0] == True:
           self.status = {'ret_code' :"pass", 'message': "Successfully pos array {} is mounted".format(array_name)}
        else:
           self.status = {'ret_code' :"fail", 'message': "failed to mount pos array {} ".format(array_name)}
        self.mnt_pos_out = mnt_status[1]

    def unmount_array(self, array_name):
        """
        Method to Unmount pos array
        """
        mnt_status = self.pos_obj.unmount_array(array_name = array_name)
        if mnt_status[0] == True:
           self.status = {'ret_code' :"pass", 'message': "Successfully pos array {}  is unmounted".format(array_name)}
        else:
           self.status = {'ret_code' :"fail", 'message': "failed to unmount pos array {}".format(array_name)}
        self.unmnt_pos_out = mnt_status[1]

    def delete_array(self, array_name ):
        """
        Method to delete the created array
        """
        del_arr_status = self.pos_obj.delete_array(array_name = array_name)
        if del_arr_status[0] == False:
           self.status = {'message':"failed to delete array {}".format(array_name),'ret_code':"fail"}
        else:
           self.status = {'message':"successfully array {} is deleted".format(array_name),'ret_code':"pass"}

    def get_array_info(self, array_name):
        """
        Method to get the array information
        """
        out = self.pos_obj.get_array_info(array_name = array_name)
        if out[0] is False:
           self.status = {'ret_code':'fail','message': 'failed to fetch information for the array {}'.format(array_name)}
        else:
           self.status = {'ret_code':'pass','message': 'Successfully fetched information for the array {}'.format(array_name)}
        self.array_info_out = out[1]
        self.array_status = out[2]
        self.array_state = out[3]

    def list_array_devices(self,array_name):
        """
        Method to fetch the list of spare,data and buffer devices
        """
        out = self.pos_obj.list_array_devices(array_name = array_name)
        if out[0] is False:
            self.status = {'ret_code':'fail','message': 'failed to fetch the device list for the array {} '.format(array_name)}
        else:
            self.status = {'ret_code':'pass','message': 'Successfully fetched the device list for the array {}'.format(array_name)}
        self.spare_disks = out[2]
        self.data_disks = out[1]
        self.buffer_disks = out[3]

    def list_arrays(self):
        """
        Method to fetch the list of arrays
        """
        out = self.pos_obj.list_array()
        if out[0] is False:
           self.status = {'ret_code':'fail','message': 'failed to fetch the list of arrays'}
        else:
           self.status = {'ret_code':'pass','message': 'Successfully fetched the list of arrays'}
        self.list_arr_out = out[1]

class volume(array_management):
    def create_vol(self, array_name, volname = None, size = None, iop = None, bandw = None):
        '''
        Method to create the volume
        '''
        if volname is None:
           volname = self.volname

        if size is None:
           size = self.params['volume_size']

        if iop is None:
           iop = self.params['iops']

        if bandw is None:
           bandw = self.params['bw']

        ret = self.pos_obj.create_vol(volumename = volname, size = size, iops = iop, bw = bandw, array_name = array_name)
        if ret[0] == False:
           self.status = {'message':"failed to create volume {}".format(volname), 'ret_code': "fail"}
        else:
           self.status = {'message':"Successfully volume {} is created".format(volname), 'ret_code': "pass"}
        self.create_vol_out = ret[1]

    def mount_vol(self, array_name, volname = None, nqn_name = None ):
        """
        Method to mount volume
        """
        if volname is None:
           volname = self.volname
        ret = self.pos_obj.mount_vol(volumename = volname, array_name = array_name)
        if nqn_name:
           ret = self.pos_obj.mount_vol(volumename = volname, nqn = nqn_name, array_name = array_name)
        if ret[0] == False:
           self.status = {'message': "Failed to mount volume {}".format(volname),'ret_code': "fail"}
        else:
           self.status = {'message': "Successfully volume {} is mounted".format(volname),'ret_code': "pass"}
        self.mount_vol_out = ret[1]

    def list_vol(self, array_name):
        """
        Method to list volume
        """
        ret = self.pos_obj.list_vol(array_name = array_name)
        if ret[0] == False:
           self.status = {'message': "Failed to list volume from array {} ".format(array_name),'ret_code': "fail"}
        else:
           self.status = {'message': "Successfully created volumes are listed from array {} ".format(array_name),'ret_code': "pass"}
        self.vols = ret[2]
        self.vol_dict = ret[3]

    def unmount_vol(self, array_name, volname = None):
        """
        Method to unmount volume
        """
        if volname is None:
          volname = self.volname

        ret = self.pos_obj.unmount_vol(volumename = volname, array_name = array_name)

        if ret[0] == False:
           self.status = {'message': "failed to unmount volume ",'ret_code':"fail"}
        else:
           self.status = {'message': "successfully volume is unmounted", 'ret_code':"pass"}
        self.unmount_vol_out = ret[1]

    def delete_vol(self, array_name , volname = None):
        """
        Method to delete the volume
        """
        if volname is None:
           volname = self.volname
        ret = self.pos_obj.delete_vol(volumename = volname, array_name = array_name )

        if ret[0] == False:
           self.status = {'message':"Deleting volume failed", 'ret_code': "fail"}
        else:
           self.status = {'message':"Successfully volume is deleted ", 'ret_code': "pass"}
        self.del_vol_out = ret[1]

    def rename_vol(self, new_volname,array_name, volname = None):
        """
        Method to rename the volume
        """
        if volname is None:
           volname = self.volname

        ret = self.pos_obj.rename_vol(volname = volname,new_volname = new_volname, array_name = array_name)
        if ret[0] == False:
           self.status = {'message':"Failed to rename volume {}".format(volname), 'ret_code': "fail"}
        else:
           self.status = {'message':"Successfully volume {} is renamed ".format(volname), 'ret_code': "pass"}
        self.rename_vol_out = ret[1]

    def create_mount_multiple(self,array_name, volname = None, size = None, iops = None, bw = None, num_vols = None, nqn_name = None):
        """
        Method Creates and mount multiple volumes in pos
        """
        if num_vols is None:
           num_vols = self.params['num_vol']

        if volname is None:
           volname = self.volname

        if size is None:
           size = self.params['volume_size']

        if iops is None:
           iops = self.params['iops']

        if bw is None:
           bw = self.params['bw']

        for i in range(num_vols):
            volume_name = volname + '_' + str(i)
            self.create_vol(volname = volume_name, size = size, iop = iops, bandw = bw,array_name = array_name )
            if self.status['ret_code'] is "fail":
               break
            else:
               self.mount_vol(volname = volume_name, nqn_name = nqn_name,array_name = array_name )
               if self.status['ret_code'] is "fail":
                  break

    def update_qos(self, array_name, volname = None, iops = None, bw = None):
        """
        method to update QOS of volume
        """
        if volname is None:
           volname = self.volname

        if iops is None:
           iops = self.params['iops']

        if bw is None:
           bw = self.params['bw']

        out = self.pos_obj.update_qos(volumename = volname, iops = iops, bw = bw, array_name = array_name)

        if out[0] is False:
           self.status = {'message':"updating QOS failed for volume {}".format(volname), 'ret_code':  "fail"}
        else:
           self.status['message'] = {'message':"Successfully updated QOS for volume {}".format(volname), 'ret_code':  "pass"}
        self.update_qos_out = out[1]

class wbt_management(volume):
    def set_gc_threshold(self, normal , urgent, array_name):
        """
        Method to set the garbage collection thnreshold
        """
        out = self.pos_obj.set_gc_threshold(normal = normal, urgent = urgent, array_name = array_name)
        if out[0] == True:
           self.status = {'ret_code':'pass','message': "successfully threshold value is set"}
        else:
           self.status = {'ret_code':'fail','message': "Failed to set the gc threshold value"}
        self.set_gc_threshold_data = out[1]

    def get_gc_status(self, array_name):
        """
        Method to get the garbage collection status
        """
        out = self.pos_obj.get_gc_status(array_name = array_name)
        if out[0] == True:
           self.status = {'ret_code':'pass','message': "successfully fetched the gc status"}
        else:
           self.status = {'ret_code':'fail','message': "Failed to fetch the gc status"}
        self.gc_status_out = out[1]
        self.gc_status_mode = out[2]

    def do_gc(self, array_name):
        """
        Method to do the garbage collection
        """
        out = self.pos_obj.do_gc(array_name = array_name)
        if out[0] == True:
           self.status = {'ret_code':'pass','message': "successfully gc is triggered"}
        else:
           self.status = {'ret_code':'fail','message': "Failed to trigger the gc"}

    def get_gc_threshold(self, array_name):
        """
        Method to get the gc threshold values
        """
        out = self.pos_obj.get_gc_threshold(array_name = array_name)
        if out[0] == True:
           self.status = {'ret_code':'pass','message': "successfully fetched the gc threshold values "}
        else:
           self.status = {'ret_code':'fail','message': "Failed to fetch the gc threshold values "}
        self.gc_threshold_values = out[1]

    def wbt_flush(self, array_name):
        """
        Method to flush the user data
        """
        out = self.pos_obj.wbt_flush(array_name = array_name)
        if out[0] is False:
           self.status = {'ret_code': 'fail', 'message': "Failed to flush the user data"}
        else:
           self.status = {'ret_code': 'pass', 'message': "Successfully flushed the user data"}
        self.wbt_flush_out = out[1]

    def read_vsamap_entry(self,vol_name, rba, array_name):
        """
        method to read vsa map entry
        """
        out = self.pos_obj.read_vsamap_entry(vol_name = vol_name, rba = rba, array_name = array_name)
        if out[0] is True:
           self.status = {'ret_code': 'pass', 'message': 'Sucessfully fetched vsa map details'}
        else:
           self.status = {'ret_code': 'fail', 'message': ' failed to fetch the vsa map details'}
        self.read_vsamap_out = out[1]

    def read_stripemap_entry(self,vsid, array_name):
        """
        method to read stripemap entry
        """
        out = self.pos_obj.read_stripemap_entry(vsid = vsid, array_name = array_name)
        if out[0] is True:
           self.status = {'ret_code': 'pass', 'message': 'Successfully fetched stripe map entry details'}
        else:
           self.status = {'ret_code': 'fail', 'message': ' failed to fetch the stripe map entry details'}
        self.stripemap_entry_out = out[1]

    def translate_device_lba(self,logical_stripe_id, logical_offset,array_name):
        """
        method to translate device lba
        """
        out = self.pos_obj.translate_device_lba(logical_stripe_id = logical_stripe_id, logical_offset = logical_offset, array_name = array_name)
        if out[0] is True:
           self.status = {'ret_code': 'pass', 'message': 'Successfully translated device lba'}
        else:
           self.status = {'ret_code': 'fail', 'message': ' failed to translate device lba'}
        self.dev_lba_out = out[1]

    def write_uncorrectable_lba(self, device_name, lba):
        """
        method to write uncottectable lba
        """
        out = self.pos_obj.write_uncorrectable_lba(device_name = device_name, lba = lba)
        if out is True:
           self.status = {'ret_code': 'pass', 'message': 'Successfully written un correctable errors to lba'}
        else:
           self.status = {'ret_code': 'fail', 'message': ' failed to write un correctable errors to lba'}

    def read_raw(self, dev, lba, count):
        """
        method to read raw data
        """
        out = self.pos_obj.read_raw(dev = dev, lba = lba, count = count)
        if out[0] is True:
           self.status = {'ret_code': 'pass', 'message': 'Successfully executed read raw command'}
        else:
           self.status = {'ret_code': 'fail', 'message': ' failed to execute read raw command'}
        self.read_raw_out = out[1]

class detach_attach_managemnt(wbt_management):
    def dev_bdf_map(self):
        """
        method to get the bdf devices map
        """
        ret = self.pos_obj.dev_bdf_map()
        if ret[0] == True:
           self.status = {'ret_code':'pass','message': "Successfully fetched bdf map"}
        else:
           self.status = {'ret_code':'fail','message': "Failed to fetch bdf map"}
        self.bdf_map_out = ret[1]

    def pci_rescan(self):
        """
        Method to re-scan pci ports
        """
        out = self.pos_obj.pci_rescan()
        if out == True:
           self.status = {'ret_code':'pass','message': "successfully pci ports  were rescanned "}
        else:
           self.status = {'ret_code':'fail','message': "Failed to scan the pci ports"}

    def get_nvme_bdf(self):
       """
       Method to get the nvme bdf's
       """
       out = self.pos_obj.get_nvme_bdf()
       if out[0] == True:
          self.status = {'ret_code':'pass','message': "successfully fetched the nvme bdf's "}
       else:
          self.status = {'ret_code':'fail','message': "Failed to fetch the nvme bdf's"}
       self.nvme_bdf = out[1]

    def device_hot_remove_by_bdf(self, bdf_addr_list):
        """
        Method to remove the device , device to be passed by its bdf
        """
        if len(bdf_addr_list) == 0:
           self.status = {'ret_code':'fail','message': 'bdf address is not passed'}
           return
        out = self.pos_obj.device_hot_remove_by_bdf(bdf_addr_list = bdf_addr_list)
        if out == True:
           self.status = {'ret_code':'pass','message': "successfully device is hot plugged by bdf "}
        else:
           self.status = {'ret_code':'fail','message': "Failed to hot plug the device by bdf"}

    def check_rebuild_status(self, array_name):
        """
        Method to check the rebuild status
        """
        out = self.pos_obj.check_rebuild_status(array_name = array_name)
        if out is False:
            self.status = {'ret_code':'fail','message': 'rebuilding failed for the array {}'.format(array_name)}
        else:
            self.status = {'ret_code':'pass','message': 'Successfully completed rebuilding'}

    def detach_dev(self,  device_name = [] ):
        """
        Method to detach a drive
        """
        if len(device_name) == 0:
           self.status = {'ret_code':'fail','message': 'Please pass a disk name '}
           return
        ret = self.pos_obj.device_hot_remove(device_list = device_name)
        if ret is False:
           self.status = {'ret_code':'fail','message': 'Failed to remove the drives {} '.format(device_name)}
        else:
           self.status = {'ret_code':'pass','message': 'Successfully removed the drives {}'.format(device_name)}

    def add_spare_drive(self,device_name, array_name):
        """
        Method to add a drive as a spare device
        """
        out = self.pos_obj.add_spare_drive(device_name = device_name, array_name = array_name)
        if out[0] is False:
            self.status = {'ret_code':'fail','message': 'Failed add the drive {}  as a spare to the array {}'.format(device_name,array_name)}
        else:
            self.status = {'ret_code':'pass','message': 'Successfully disk {} is added as a spare to the array {}'.format(device_name,array_name)}

    def remove_spare_drive(self,device_name, array_name):
        """
        Method to add a drive as a spare device
        """
        out = self.pos_obj.remove_spare_drive(device_name = device_name, array_name = array_name)
        if out is False:
           self.status = {'ret_code':'fail','message': 'Failed to remove the spare drive {} from the array {}'.format(device_name, array_name)}
        else:
           self.status = {'ret_code':'pass','message': 'Successfully the spare drive {} is removed from the array {}'.format(device_name, array_name)}

class Nvmf_transport(detach_attach_managemnt):

    def add_nvmf_listner(self, mellanox_interface, nqn_name = None, port = None, transport = None):
        """
        Method to add listner address to nvmf SS
        """
        if nqn_name is None:
           nqn_name = self.nqn_name

        if port is None:
           port = self.params['port']

        if transport is None:
           transport_protocol = self.params['transport_protocol']

        out = self.pos_obj.nvmf_add_listner(nqn_name = nqn_name, mellanox_interface = mellanox_interface, port = port, transport = transport_protocol)

        if out == True:
           self.status = {'ret_code':'pass','message':'Successfully added listner to nqn name {}'.format(nqn_name)}
        else:
           self.status = {'ret_code':'fail','message':'Failed to add listner to nqn name {}'.format(nqn_name)}

    def create_transport(self, buff_cache_size = None, num_shared_buffers = None, transport_protocol = None):
        """
        method: Creates transport for Nvmf
        """
        if buff_cache_size is None:
           buff_cache_size = self.params['buff_cache_size']

        if num_shared_buffers is None:
           num_shared_buffers = self.params['num_shared_buffers']

        if transport_protocol is None:
           transport_protocol = self.params['transport_protocol']

        out = self.pos_obj.create_transport(buf_cache_size = buff_cache_size, num_shared_buffers = num_shared_buffers, transport = transport_protocol)

        if out == True:
           self.status = {'ret_code':'pass','message':'Successfully created nvmf transport'}
        else:
           self.status = {'ret_code':'fail','message':'failed to create nvmf transport '}

    def create_Nvmf_SS(self, nqn_name = None, serial_number = None, model_number = None, ss_count = None,ns_count = None):
        """
        Method to create Nvmf SS on pos
        """
        if ss_count is None:
           count = 1
        else:
           count = ss_count
        for i in range(1, count + 1):
            if serial_number is None:
               serial_number = self.params['serial_number']

            if nqn_name is None:
               nqn_name = self.pos_obj.generate_nqn_name()

            if model_number is None:
               model_number = self.params['model_number']

            if ns_count is None:
               ns_count = self.params['ns_count']

            out = self.pos_obj.create_nvmf_subs(nqn_name = nqn_name, s = serial_number, d = model_number, ns_count = ns_count)

            if out[0] == False:
               self.status = {'ret_code':'fail','message': "Failed to create Nvmf Subsystem! please check manually"}
               break
            else:
               self.status = {'ret_code':'pass','message': "Nvmf SS created!"}
               self.nqn_name = nqn_name
               nqn_name = None

class PoSos(Nvmf_transport):

    def __init__(self, pos_obj, params = {'iops' : 0, 'bw' :0, 'num_spare_devs' : 1,'num_writebuff' : 1,'num_datastorage' : 3, 'volume_size' : 2147483648, 'volume_name' : 'iBOF_Vol', 'num_vol' : 1, 'buff_cache_size' : 64, 'num_shared_buffers' : 4096, 'port' :1158, 'transport_protocol' : 'TCP','serial_number' : 'IBOF00000000000001', 'model_number' : "IBOF_VOLUME", "ns_count": 256} ):

        self.pos_obj = pos_obj
        self.params = params
        self.status = {'ret_code':'pass','message':'NA'}
        self.volname = self.params['volume_name']
