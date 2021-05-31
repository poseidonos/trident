class Hostconf():

        def __init__(self, client_obj, params = {'port' : 1158,'transport' : 'tcp', 'fs_format' : 'ext3', 'io_mode' : True}):
             
            """
            Class servers all methods for all client related operations in iBOF
            """
            self.status = {'ret_code':'pass','message':'NA'}
            self.params = params
            self.client_obj = client_obj
            self.device_FS_list = []

        def nvme_connect(self, nqn_name, ip, port = None, transport = None):
            """
            Method : Connects subsystem to the host instance
            """
            if port is None:
               port = self.params['port']
           
            if transport is None:
               t = self.params['transport']

            out = self.client_obj.nvme_connect(nqn_name = nqn_name, mellanox_switch_ip = ip, port = port, transport = t)
            if out is True:
               self.status = {'ret_code': 'pass', 'message': 'Connected Nvmf subsytem to the client'}
            else:
               self.status = {'ret_code': 'fail', 'message': 'Failed to connect'}
               
        def nvme_discover(self, mellanox_switch_ip, nqn_name, port = None, transport = None):
            """
            Method : discovers nvmf subsystems
            """
            if port is None:
               port = self.params['port']

            if transport is None:
               transport = self.params['transport']

            out = self.client_obj.nvme_discover(nqn_name = nqn_name, mellanox_switch_ip = mellanox_switch_ip, port = port, transport = transport)
            if out is True:
                self.status = {'ret_code' : 'pass', 'message' : 'Discoverd nvmf subsystem {}'.format(nqn_name)}
            else:
                self.status = {'ret_code': 'fail', 'message': 'failed to discover nvmf subsystem {}'.format(nqn_name)}

        def nvme_disconnect(self):
            """
            Method : Disconnects nvme subsystem from host instance
            """
            out = self.client_obj.disconnect_rdma()
            if out is True:
               self.status = {'ret_code':'pass','message':'Successfully disconnected subsystem'}
            else:
               self.status = {'ret_code':'fail','message':'failed to disconnect susbsystem'}

        def list_nvme(self, mn = "IBOF_VOLUME"):
            """
            Method : lists the connected nvme subsytems at the host
            """
            out = self.client_obj.nvme_list(model_name = mn)
            
            if out[0] == True:
               self.status = {'ret_code':'pass','message':'Successfully listed connected nvme devices '}
            else:
               self.status = {'ret_code':'fail','message':'Failed to list connected nvme devices'}
            self.device_list = out[1]
 
        def nvme_format(self, dev_list = []):
            """
            Method : format the device using nvme cli
            """
            if len(dev_list) == 0:
               self.status = {'ret_code':'fail','message':'No device is passed'}
               return 
            for dev in dev_list:
                out = self.client_obj.nvme_format(device_name = dev)
                if out == True:
                   self.status = {'ret_code':'pass','message':'successfully device is formatted'}
                else:
                   self.status = {'ret_code':'fail','message':'failed to format the device'}
                   break

        def create_FS(self, dev_list, format_type = None):
            """
            Method to create MKFS on the client machine
            """
            if format_type is None:
               format_type = self.params['fs_format']
               
            out = self.client_obj.create_File_system(device_list = dev_list, fs_format = format_type)

            if out is False:
               self.status = {'ret_code':'fail','message':'Failed to Create MKFS, Please check again!'}
            else:
               self.status = {'ret_code':'pass','message': "Created and formated Device"}

        def mount_FS(self, dev_list, opt = None, fs_mount = 'tmp'):
            """
            Method to mount a give device to dir
            """
            out = self.client_obj.mount_FS(device_list = dev_list, options = opt, fs_mount_dir = fs_mount)

            if out[0] is False:
               self.status = {'ret_code':'fail','message':'Failed to Mount and Format, Please check again!'}
            else:
               self.status = {'ret_code':'pass','message':"FS created on {} with {}".format(dev_list, fs_mount)}
            self.device_FS_list = list(out[1].values())

        def unmount_FS(self, unmount_dir):
            """
            Mehtod to unmount a dir
            """
            out = self.client_obj.unmount_FS(fs_mount_pt = unmount_dir)

            if out is False:
               self.status = {'ret_code':'fail','message':'Failed to unmount, Please check again!'}
            else:
               self.status = {'ret_code':'pass','message':"Successfully FS is unmounted "}

        def nvme_show_regs(self,device_name,search_string = None):
            """
            Method to execute nvme show-regs on the device
            params  :device_name : Name of the nvme device
                    : search_string : string to be searched in output
            """
            out = self.client_obj.nvme_show_regs(device_name = device_name, search_string = search_string)
            if out[0] is False:
               self.status = {'ret_code':'fail','message':'Failed to execute nvme show-regs on the device {}'.format(device_name)}
            else:
               self.status = {'ret_code':'pass','message': "Successfully executed nvme show-regs on the device {}".format(device_name)}
            self.nvme_show_regs_out = out[1]

        def nvme_ns_rescan(self,cntlr_name):
            """
            Method to execute nvme ns-rescan on the controller
            """
            out = self.client_obj.nvme_ns_rescan(cntlr_name = cntlr_name)
            if out is False:
               self.status = {'ret_code':'fail','message':'Failed to execute nvme ns-rescan on the controller {}'.format(cntlr_name)}
            else:
               self.status = {'ret_code':'pass','message': "Successfully executed nvme ns-rescan on the controller {}".format(cntlr_name)}


        def nvme_id_ctrl(self,device_name,search_string = None):
            """
            Method to execute nvme id-ctrl on the device
            """
            out = self.client_obj.nvme_id_ctrl(device_name = device_name, search_string = search_string)
            if out[0] is False:
               self.status = {'ret_code':'fail','message':'Failed to execute nvme id-ctrl on the device {}'.format(device_name)}
            else:
               self.status = {'ret_code':'pass','message': "Successfully executed nvme id-ctrl on the device {}".format(device_name)}
            self.nvme_id_ctrl_out = out[1]

        def nvme_smart_log(self,device_name,search_string = None):
            """
            Method to execute nvme smart-log on the device
            """
            out = self.client_obj.nvme_smart_log(device_name = device_name, search_string = search_string)
            if out[0] is False:
               self.status = {'ret_code':'fail','message':'Failed to execute nvme smart-log on the device {}'.format(device_name)}
            else:
               self.status = {'ret_code':'pass','message': "Successfully executed nvme smart-log on the device {}".format(device_name)}
            self.nvme_smart_log_out = out[1]

        def nvme_list_subsys(self,device_name):
            """
            Method to execute nvme list-subsys on the device
            """
            out = self.client_obj.nvme_list_subsys(device_name = device_name)
            if out[0] is False:
               self.status = {'ret_code':'fail','message':'Failed to execute nvme list-subsys on the device {}'.format(device_name)}
            else:
               self.status = {'ret_code':'pass','message': "Successfully executed nvme list-subsys on the device {}".format(device_name)}
            self.nvme_list_subsys_out = out[1]

        def fio_generic_runner(self, devices, fio_data = None, io_mode = None):
            """
            Method to run fio
            """
            if io_mode is None:
               io_mode = self.params['io_mode']

            out = self.client_obj.fio_generic_runner(devices = devices, fio_user_data = fio_data,IO_mode = io_mode)
            if out[0] is True:
               self.status = {'ret_code':'pass','message':'fio passed'}
            else:
               self.status = {'ret_code':'fail','message':'fio failed'}

        def is_file_present(self,file_path):
            """
            Method to check whether file exists or not 
            """
            out = self.client_obj.is_file_present(file_path = file_path)
            if out is False:
               self.status = {'ret_code':'fail','message':'File is not present in the system'}
            else:
               self.status = {'ret_code':'pass','message': "File is present in the system"}

        def reboot_reconnect(self):
            """
            method to reboot and reconnnect
            """
            out = self.client_obj.reboot_with_reconnect(timeout = 1000)
            if out[1] is False:
               self.status = {'ret_code' : 'fail', 'message':'failed to bring up node'}
            else:
               self.status = {'ret_code':'pass','message': "Node UP "}
            self.client_obj = out[0]
          
        def ctrlr_count(self):
            """
            method to get the count of controllers connected
            """
            out = self.client_obj.ctrlr_count()
            if out[0] is False:
               self.status = {'ret_code' : 'fail', 'message':"failed to get controller count"}
            else:
               self.status = {'ret_code':'pass','message': "connected controller count is {}".format(out[1])}
            self.ctrlr_info = out[1]

        def nvme_flush(self, dev_list):
            """
            method to do nvme flush on passed connected nvme devices
            """
            if len(dev_list) == 0:
               self.status = {'ret_code':'fail','message':'No device is passed'}
               return

            out = self.client_obj.nvme_flush(dev_list = dev_list)
            if out is True:
               self.status = {'ret_code': 'pass', 'message': "nvme flush passed on all connected devices"}
            else:
               self.status = {'ret_code': 'fail', 'message': "nvme flush failed on all connected devices"}
