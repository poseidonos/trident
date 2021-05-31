import logger, time, threading, os, re, random, json, traceback
from datetime import datetime
from node import SSHclient
logger = logger.get_logger(__name__)
import node

class Client():
    """
    Client class consisting of utilities methods
    """
    def __init__(self,ssh_obj):
        """
        :param ssh_obj: ssh object needs to be passed created during starting of execution
        """
        self.ssh_obj = ssh_obj

    def close(self):
        """
        Method to close the ssh object
        """
        self.ssh_obj.close()

    def reboot_node(self):
        """
        Method to reboot the node
        :return:True/False
        """
        try:
          stdoutlines = []
          shell = self.ssh_obj.ssh.invoke_shell()
          node._shell_receive(shell, stdoutlines)

          if self.ssh_obj.username == "root":
             shell.send("shutdown -r now  " + '\n')
          else:
             shell.send("sudo shutdown -r now  " + '\n')
             shell.send(self.ssh_obj.password + "\n")
             node._shell_receive(shell, stdoutlines)
             shell.send(self.ssh_obj.password + "\n")

          logger.info("waiting 10 seconds for reboot")
          time.sleep(10)
          logger.info("Reboot node sucessfull")
          return True
        except Exception as e:
            logger.error("Error rebooting node because of Error {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def reboot_with_reconnect(self,timeout=600):
        """
        Methods: To reboot the node and wait for it come up
        :param timeout: time to wait for node to come up after reboot
        :return: New ssh object
        """
        self.reboot_node()
        count = 0
        new_ssh = None
        node_stats = None

        while True :
             try:
                new_ssh = SSHclient(self.ssh_obj.hostname, self.ssh_obj.username, self.ssh_obj.password)
             except Exception as e:
                 logger.info("node is still down {}".format(e))
                 time.sleep(60)
                 logger.info("waiting 60 seconds node to come  up ")
             count=count+60   
             if new_ssh:
                node_status = new_ssh.get_node_status()
             if count>timeout or node_stats==True:
                 break

        if new_ssh:
           return new_ssh, True
        else:
           logger.error(traceback.format_exc()) 
           raise ConnectionError("Node failed to come up")

    def reconnect(self,timeout=600):
        """
        Methods: To reboot the node and wait for it come up
        :param timeout: time to wait for node to come up after reboot
        :return: New ssh object
        """
        count = 0
        new_ssh_obj=None
        node_status=None

        while True :
             try:
                new_ssh_obj = SSHclient(self.ssh_obj.hostname, self.ssh_obj.username, self.ssh_obj.password)
             except Exception as e:
                 logger.info("node is still down {}".format(e))
             logger.info("waiting 60 seconds node to come  up ")
             time.sleep(60)
             count=count+60
             if new_ssh_obj:
                node_status = new_ssh_obj.get_node_status()
             if count>timeout or node_status==True:
                 break

        if new_ssh_obj:
           return new_ssh_obj
        else:
           logger.error(traceback.format_exc()) 
           raise ConnectionError("Node failed to come up")

    def nvme(self,nvme_cmd):
        """
        Methods: Execution of nvme command
        :param:  nvme_cmd nvme command
        returns: Execution output for nvme command
        """
        logger.info("Executing NVMe CLI client commands")
        nvme_cmd_output=self.ssh_obj.execute(nvme_cmd)
        return nvme_cmd_output

    def nvme_format(self,device_name):
        """
        Method to format device using nvme cli
        Params : device_name : list of devices to be formatted using nvme cli
        return : Bool ( True/False)
        """
        try:
          logger.info("Formatting the device {} ".format(device_name))
          cmd  = "nvme format {}".format(device_name)
          out = self.nvme(cmd)
          if 'Success formatting namespace' in out[0]:
             logger.info("Successfully formatted the device ") 
          else:
             raise Exception("formatting nvme device failed")
        except Exception as e:
           logger.error("nvme format command failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False
        return True

    def nvme_id_ctrl(self,device_name,search_string = None):
        """
        Method to execute nvme id-ctrl nvme cli
        Params : device_name : list of devices to be formatted using nvme cli
               : search_string : to search for specific string in output 
        return : Output, Bool ( True/False)
        """
        try:
          logger.info("Executing id-ctrl on  the device {} ".format(device_name))
          if search_string:
             cmd  = "nvme id-ctrl {} | grep -w {}".format(device_name,search_string)
          else:
             cmd = "nvme id-ctrl {} ".format(device_name)
          out = self.ssh_obj.execute(cmd)
          if len(out) != 0 :
             logger.info("Successfully executed nvme id-ctrl on the device {}".format(device_name))
             return True,out
          else:
             raise Exception("Failed to execute nvme id-ctrl on the device {}".format(device_name))
        except Exception as e:
           logger.error("nvme id-ctrl command failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False,out

    def nvme_ns_rescan(self,cntlr_name):
        """
        Method to execute nvme ns-rescan nvme cli
        Params : cntlr_name : name of the controller to be rescaned
        return : Bool ( True/False)
        """
        try:
          logger.info("Executing ns-rescan on  the controller {} ".format(cntlr_name))
          cmd = "nvme ns-rescan {}".format(cntlr_name)
          out = self.ssh_obj.execute(cmd)
          if "No such file or directory" in out :
              raise Exception (" Failed to rescan the controller {}".format(cntlr_name))
          else:
             logger.info("Successfully rescaned the controller {}".format(cntlr_name))
             return True
        except Exception as e:
           logger.error("nvme ns-rescan command failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False

    def nvme_show_regs(self,device_name,search_string = None):
        """
        Method to execute nvme show-regs nvme cli
        Params : device_name : list of devices to be formatted using nvme cli
               : search_string : to search for specific string in output
        return : Output, Bool ( True/False)
        """
        try:
          logger.info("Executing show-regs on  the device {} ".format(device_name))
          if search_string:
             cmd  = "nvme show-regs -H {} | grep -w {}".format(device_name,search_string)
          else:
             cmd = "nvme show-regs -H {} ".format(device_name)
          out = self.ssh_obj.execute(cmd)
          logger.info("output of the command {} is {} ".format(cmd,out))
          if len(out) != 0 :
             logger.info("Successfully executed nvme show-regs on the device {}".format(device_name))
             return True,out
          else:
             raise Exception("Failed to execute nvme show-regs on the device {}".format(device_name))
        except Exception as e:
             logger.error("nvme show-regs command failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False,out

    def nvme_list_subsys(self,device_name):
        """
        Method to execute nvme list-subsys nvme cli
        Params : device_name : list of devices to be formatted using nvme cli
        return : Output, Bool ( True/False)
        """
        try:
          logger.info("Executing list-subsys on  the device {} ".format(device_name))
          cmd = "nvme list-subsys {} -o json ".format(device_name)
          out = self.ssh_obj.execute(cmd)
          out1 = "".join(out)
          json_out = json.loads(out1)
          logger.info("output of the nvme list-subsys is {} ".format(json_out))
          if "Error" in out:
             raise Exception("Failed to execute nvme list-subsys on device {}".format(device_name))
          else:
             logger.info("Successfully executed nvme list-subsys on device {}".format(device_name))
             return True,json_out
        except Exception as e:
            logger.error("nvme list-subsys command failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False,None

    def nvme_smart_log(self,device_name,search_string = None):
        """
        Method to execute nvme smart-log nvme cli
        Params : device_name : list of devices to be formatted using nvme cli
               : search_string : to search for specific string in output
        return : Output, Bool ( True/False)
        """
        try:
          logger.info("Executing smart-log  on  the device {} ".format(device_name))
          if search_string:
             cmd  = "nvme smart-log {} | grep {} | awk  '{{print $3}}'".format(device_name, search_string)
             logger.info(cmd)
          else:
             cmd = "nvme smart-log {} ".format(device_name)
          out = self.ssh_obj.execute(cmd)
          if len(out) != 0 :
             logger.info("Successfully executed nvme smart-log on the device {}".format(device_name))
             return True,out
          else:
             raise Exception ("Failed to execute nvme smart-log on the device {}".format(device_name))
        except Exception as e:
             logger.error("nvme smart-log command failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False,None

    def os_version(self):
        """
        :method To find OS version
        :Params
        :return type String
        """
        flag = [version for version in self.ssh_obj.execute("cat /etc/os-release") if "ubuntu" in version]
        if len(flag):
                logger.info("OS version is %s"%(flag[0].split("=")[1].strip("\n") + flag[1].split("=")[1].strip()))
                return  flag[0].split("=")[1].strip("\n") + flag[1].split("=")[1].strip()

    def fio_generic_runner(self, devices, fio_user_data = None, IO_mode = True):
        """
        :method To run user provided fio cmd line from user
        :params fio_user_data :fio cmd line (default :none)
                devices: takes a list of either mount points or raw devices
                IO_mode : RAW IO(True)/File IO(False)
        :return : Boolean,fio_output
        """
        try:
          if len(devices) is 1 and IO_mode is True:
             filename = devices[0]
          elif len(devices) is 1 and IO_mode is False:
             filename = devices[0] +'/file.bin'
          elif len(devices) > 1 and IO_mode is True:
             filename = ':'.join(devices)
          elif len(devices) > 1 and IO_mode is False:
             filename = "/file.bin:".join(devices)
             filename += "/file.bin"
          else:
             raise Exception("no devices found ")
          logger.info(fio_user_data)
          if  fio_user_data and IO_mode == False:
              logger.info("Executing fio with user data using  FILE IO")
              fio_cli = fio_user_data + " --filename={}".format(filename)
          elif fio_user_data and IO_mode == True:
               logger.info("Executing fio with user data using  RAW IO")
               fio_cli = fio_user_data + " --filename={}".format(filename)
          elif IO_mode == False:
               logger.info("Executing the default fio command with File IO ")
               fio_cli = "fio --name=S_W --runtime=5 --ioengine=libaio --iodepth=16 --rw=write --size=1g --bs=1m --filename={}".format(filename)
          else:
               logger.info("Executing default fio command with RAW IO")
               fio_cli = "fio --name=S_W  --runtime=5 --ioengine=libaio  --iodepth=16 --rw=write --size=1g --bs=1m --direct=1 --filename={}".format(filename)

          outfio = self.ssh_obj.execute(command = fio_cli,get_pty = True)
          logger.info(''.join(outfio)) 
          return True, outfio
        except Exception as e :
             logger.error("Fio failed due to {}".format(e))
             logger.error(traceback.format_exc())
             return (False,None)

    def is_file_present(self,file_path):
        """
        Method to verif if file present of not
        :param file_path: file path
        :return: Boolean True or False
        """
        try:
          out = self.ssh_obj.execute("if test -f {}; then     echo ' exist'; fi".format(file_path))
          if out:
             if "exist" in out[0]:
                logger.info("File  {} exist".format(file_path))
                return True
          else:
             raise Exception ("file {}  does not exist".format(file_path))
        except Exception as e:
             logger.error("command failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False
   
    def create_File_system(self, device_list, fs_format = "ext3"):
        """
        Creates MKFS FS on different devices
        """
        try:
          if len(device_list) == 0:
             raise Exception("No devices Passed")
          else:
             for device in device_list:
                 if (fs_format == "xfs"):
                    format_cmd = "yes |sudo mkfs.{} -f  {}".format(fs_format, device)
                 else:
                    format_cmd = "yes |sudo mkfs.{} {}".format(fs_format, device)       
                 self.ssh_obj.execute(format_cmd, get_pty = True)
             return True
        except Exception as e:
            logger.error("command failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False   

    def mount_FS(self, device_list, fs_mount_dir = None, options = None):
        """
        method to Mount Fs to device
        params:
        device_list : [devices to mount]
        fs_mount_dir : if None will create dir in /tmp
        option if not None will add to mount cmd
        eg --force
        :return (Bool,[dir_list])
        """
        out = {}
        logger.info("device_list={}".format(device_list))
        if len(device_list) == 0:
           raise Exception("No devices Passed")
        else:
           try: 
             for device in device_list:
                 device_str = device.split("/dev/")[1]
                 if fs_mount_dir :
                    device_str = device.split("/dev/")[1]
                    fs_mount = "/{}/media_{}".format(fs_mount_dir, device_str)
                 else:
                    fs_mount = "/tmp/media_{}".format(device_str)
                 logger.info(fs_mount)
                 if self.is_dir_present(fs_mount) == True:
                    logger.error("{} found ..creating random dir inside {} to avoid duplication".format(fs_mount, fs_mount))
                    fs_mount = "{}/{}".format(fs_mount, str(random.randint(0,1000)))
                 if self.is_dir_present(fs_mount) == True:
                    raise Exception ("{} already Exist, Please Unmount and Try again!".format(fs_mount))
                 fs_make = "mkdir -p {}".format(fs_mount)
                 if options:
                    f_mount = "mount {} {} {}".format(device, fs_mount, options)
                 else:
                    f_mount = "mount {} {}".format(device, fs_mount)
                 try:
                   self.ssh_obj.execute(fs_make, get_pty = True)
                   self.ssh_obj.execute(f_mount, get_pty = True)
                   mnt_verify_cmd = "mount | grep {} ".format(fs_mount)
                   verify = self.ssh_obj.execute(mnt_verify_cmd)
                   if len(verify) == 0:
                      raise Exception("Mount Failed! PLease try again")
                   else:
                      for mount_pts_devices in verify:
                          if  fs_mount in mount_pts_devices:
                               out[device] = fs_mount
                 except Exception as e:
                     logger.error("Mounting {} to {} failed due to {}".format(fs_mount, device, e))
                     logger.error(traceback.format_exc())
                     return (False,None)
           except Exception as e:
               logger.error("command execution failed with exception {}".format(e))
               return (False,None)
           return (True,out) 

    def unmount_FS(self, fs_mount_pt):
        """
        method to unmount file system
        params : fs_mount_pt : Name of the directory to unmount
        :return bool
        """
        try:
          if len(fs_mount_pt) == 0:
             raise Exception("No mount point is specified")
          else:
             for mnt in fs_mount_pt: 
                 umount_cmd = "umount {}".format(mnt)
                 self.ssh_obj.execute(umount_cmd)
                 logger.info("Successfully mount point {} is unmounted".format(mnt))
                 verify = self.ssh_obj.execute("mount")
                 for mount_pts_devices in verify:
                     if mnt in mount_pts_devices:
                        raise Exception ("failed to unmount the mount point {}".format(mnt))
                     else:
                        logger.info("deleting filesystem after unmounting")
                        self.delete_FS(fs_mount_pt = mnt)
             return True
        except Exception as e:
             logger.error("command execution failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False
   
    def delete_FS(self,fs_mount_pt = None):
        """
        Method to delete a directory, used to delete directory after unmount
        params : fs_mount_pt = dir_name
        :return Bool
        """
        try:
          rm_cmd = "rm -fr {}".format(fs_mount_pt)
          self.ssh_obj.execute(rm_cmd)
          if self.is_dir_present(fs_mount_pt) is True:
             raise Exception("file system found after deletion")
          else:
             return True
        except Exception as e:
             logger.error("command excution failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False

    def is_dir_present(self,dir_path):
        """
        Method to verif if directory is present or not
        :param dir_path:  path to directory
        :return: Boolean True or False
        """
        try:
          out = self.ssh_obj.execute("if test -d {}; then     echo ' exist'; fi".format(dir_path))
          if out:
             if "exist" in out:
                logger.info("directory  {} exist".format(dir_path))
                return True
          else:
             logger.warning("directory {}  does not exist".format(dir_path))
             return False
        except Exception as e:
             logger.error("error finding directory {}".format(e))
             return False
			
    def nvme_connect(self, nqn_name, mellanox_switch_ip, port, transport = 'TCP'):
        """
        Method to connect rdma at initiator
        params:
        nqn_name:nqn random name
        mellanox_switch_ip: mellanox switch interface ip
        port: switch port ip
        return True/False
        """
        try:
           for cmd in ["modprobe mlx5_core","modprobe mlx4_core","modprobe mlx4_ib","modprobe nvme"]:
               self.ssh_obj.execute(cmd)
           logger.info("loading {} Drivers".format(transport))
           if transport.lower() == "rdma":
              cmd = "modprobe nvme_rdma"
              self.ssh_obj.execute(cmd)
           elif transport.lower() ==  "tcp":
              cmd = "modprobe nvme_tcp"
              self.ssh_obj.execute(cmd)
           else:
              raise Exception("invalid Transport protocol mentioned")
  
           cmd="nvme connect -t {} -s {} -a {} -n {}".format(transport.lower(), port, mellanox_switch_ip, nqn_name)
           logger.info("Running command {}".format(cmd))
           out = self.ssh_obj.execute(cmd)
           return True
        except Exception as e:
           logger.error("command execution failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False

    def ctrlr_count(self):
        """ 
        method to find the count of number of controllers connected at the client machine
        return (bool,count)
        """
        cmd = "ls /dev/nvme*"
        out = self.ssh_obj.execute(cmd)
        if len(out)  < 2 :
           logger.error("No controllers found")
           return (False, None)
        else:
           out.remove('/dev/nvme-fabrics\n') 
        temp, final = [], []
        for device in out:
            ctrlr = re.findall('/dev/nvme[0-9]+', device)
            temp.append(ctrlr[0])
         
        for i in temp:
            if i not in final:
               final.append(i)
        logger.info(final)

        return (True, final)

    def disconnect_rdma(self, timeout = 60):
        """
        Method to disconnect rdma at initiator
        return True/False
        """
        try:
          logger.info("Disconnecting nvme devices from client")
          count = 0
           
          while True:
               out = self.ctrlr_count()
               if out[1] is None:
                  logger.info("no devices present")
                  return True
               for ctrlr in out[1]:
                   cmd = "nvme disconnect -d {}".format(ctrlr)
                   out = self.ssh_obj.execute(cmd, get_pty = True)

               nvme_out = self.nvme_list()
               if len(nvme_out[1]) == 0:
                  logger.info("Nvme disconnect passed")
                  return True
               else:
                  logger.info("retrying disconnect in 10 seconds")
                  count += 10
                  time.sleep(10)
                  if count > timeout:
                     break
          if len(nvme_out[1]) != 0:
             raise Exception("nvme disconnect failed")  
        except Exception as e:  
            logger.error("command failed wth exception {}".format(e))
            logger.error(traceback.format_exc())
            return False
     
    def nvme_list(self, model_name= "IBOF_VOLUME"):
        """
        Method to get the nvme list
        :param : model_name : 
        return list of nvme drives
        """
        try:
           cmd= "nvme list"  
           out = self.nvme(cmd)
           nvme_list_out = []
           for line in out:
                logger.info(line)
                if model_name in line:
                   list_out = line.split(" ")
                   nvme_list_out.append(str(list_out[0]))
           if len(nvme_list_out) == 0:
              logger.debug("no devices listed")
              return False,nvme_list_out
        except Exception as e:
           logger.error("command execution failed with exception {} ".format(e))
           logger.error(traceback.format_exc())
           return False,nvme_list_out
        return True, nvme_list_out
    
    def nvme_discover(self, nqn_name, mellanox_switch_ip, port, transport = 'tcp'):
        """
        method to discover nvme subsystem
        params :
              nqn_name : Subsystem name 
              mellanox_switch_ip : mlnx_ip
              port : port number
        return Bool
        """
        try:
          self.ssh_obj.execute("modprobe nvme")
          self.ssh_obj.execute("modprobe mlx4_core")
          self.ssh_obj.execute("modprobe mlx4_ib")
          self.ssh_obj.execute("modprobe mlx5_core")
          self.ssh_obj.execute("modprobe mlx5_ib")

          if transport =='tcp':
             logger.info("loading tcp drivers")
             driver_cmd = "modprobe nvme_tcp"
             self.ssh_obj.execute(driver_cmd)
          else:
             driver_cmd = "modprobe nvme_rdma"
             self.ssh_obj.execute(driver_cmd)
          discover_cmd = "nvme discover --transport={} --traddr={} -s {}  --hostnqn={}".format(transport,mellanox_switch_ip, port, nqn_name)
          logger.info("Running command {}".format(discover_cmd))
          out = self.ssh_obj.execute(discover_cmd)
          flag = 0
          for line in out:
              if nqn_name[0] in line or mellanox_switch_ip in line:
                 flag = 1
                 break
          if flag == 1:
             return True
          else:
             logger.error("Discover failed")
             return False
        except Exception as e:
             logger.error("command execution failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False

    def nvme_flush(self, dev_list):
        """
        methood to execute nvme flush 
        :params : devices_list : list of nvme devices to be passed in list
        return Bool
        """
        try:
          for dev in dev_list:
            cmd = "nvme flush {} -n 0x1".format(dev)
            out = self.ssh_obj.execute(cmd)
            logger.info(out)
            out1 = ''.join(out)
            logger.info(out1)
            if "NVMe Flush: success" in out[0].strip():
              logger.info("successfully executed nvme flush on device {}".format(dev))
            else:
              raise Exception ("nvme flush command failed on device {}".format(dev))
        except Exception as e:
           logger.error("command execution failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False
        return True
