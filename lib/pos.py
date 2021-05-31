import re, os, json, time, string, random, threading, math, traceback
import logger as logging
from datetime import datetime, timedelta
from node import SSHclient
from utils import Client

logger= logging.get_logger(__name__)
class pos_management(Client):
    def setup_env_pos(self):
         """
         Method : to move the nvme drives from kernel mode to user mode
         """
         try:
             cmd = "{}/script/setup_env.sh".format(self.pos_path)
             out = self.ssh_obj.execute(cmd)
             if 'Setup env. done' in out[-1] :
                 logger.info('Bringing drives from kernel mode to user mode successfull')
                 return True
             else:
                raise Exception ("failed bring the drives from kernel mode to user mode")
         except Exception as e:
             logger.error("command execution failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False
			 
    def start_pos_os(self):
        """
        Method to start the pos os
        return True/False
        """
        try:
           logger.info("Verifying if any pos instance is UP")
           out = self.get_pos_info_system()
           if out[0] is False:
              logger.info("pos os is not running creating a fresh instance")
           else:
              logger.info("Killing the exisiting PID and creating new pos os instance")
              out = self.stop_pos_os(grace_shutdown = False)
              if out is False:
                 logger.error("Failed to kill pos os")
                 return False
           udev_install = self.udev_install()
           if udev_install == False:
              logger.error("Failed to execute make udev_install command")
              return False
           self.out = self.ssh_obj.run_async("{}/bin/{} >>pos_console.log".format(self.pos_path, "poseidonos"))
           logger.info("waiting for iBOF logs")
           time.sleep(5)
           if self.out.is_complete() is False:
              return True
           else:
              raise Exception("failed to start pos os")
        except Exception as e:
             logger.info("Failed to start pos os due to {}".format(e))
             logger.error(traceback.format_exc())
             return False

    def get_pos_info_system(self):
        """
        method to get the system info details
        :return :Tuple (Boolean,output)
        """
        try:
           cmd = "info"
           out = self.run_cli_command(cmd, command_type='system')
           if out[0] == True:
              if out[1]["status_code"] == 0:
                 logger.info("Successfully fetched pos os system information")
                 return (True, out[1])
              else:
                 logger.warning("failed to fetch pos os system with status code {}".format(out[1]["status_code"]))
                 return False, out[1]
           else:
              logger.error("info command execution failed with error {}".format(out[1]))
              return False, out[1]
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False, out[1]

    def pos_version(self):
         """
         method to get cli system verison
         :return :Tuple (Boolean,output)
         """
         try:
           cmd = "version"
           out = self.run_cli_command(cmd, command_type='system')
           if out[0] == True:
              if out[1]["status_code"] == 0:
                 logger.info("Successfully fetched pos os version ")
                 return (True, out[1])
              else:
                 raise Exception ("failed to execute version command with status code {}".format(out[1]["status_code"]))
           else:
              raise Exception ("version command execution failed with error {}".format(out[1]))
         except Exception as e:
             logger.error("command execution failed because of {}".format(e))
             logger.error(traceback.format_exc())
             return False, out[1]

    def stop_pos_os(self, grace_shutdown = True):
        """
        Method to stop the pos process
        :parameters : grace_shutdown by default set to True to do graceful shutdown of pos os
        return Bool
        """
        if grace_shutdown:
            try:
                arr_flag = True
                arr_list = []
                list_arr_out = self.list_array()
                if list_arr_out[0] == True:
                   logger.info("successfully fetched the list of arrays")
                else:
                   raise Exception ("Failed to get the list of arrays")
                for key,val in list_arr_out[1].items():
                    if val['status'].lower() == 'unmounted':
                       logger.info("array {} is not mounted ".format(key))
                    else:
                       logger.info("unmounting array {}".format(key))
                       unmount_out = self.unmount_array(array_name = key)
                       if unmount_out[0] == True:
                          logger.info("Successfully array {} is unmounted ".format(key))
                       else:
                          logger.error("failed to unmount array {}".format(key))
                          arr_flag = False
                          arr_list.append(key)
                if arr_flag == False:
                   logger.error("unmount failed for the list of arrays {}".format(arr_list))
                   return False
                out = self.run_cli_command('exit', command_type='system')
                if out[0] == True:
                    if out[1]["status_code"] == 0 :
                       logger.info("iBOFOS was stopped successfully!!!")
                       time.sleep(15)
                       return True
                    else:
                       raise Exception ("Failed to kill the pos os with status code {}".format(out[1]["status_code"]))
            except:
                logger.error("This method failed to kill the pos os please check the log for instance where it killed")
                logger.error(traceback.format_exc())
                return False
        else:
            try:
                self.ssh_obj.execute(command = "pgrep poseidonos | xargs kill -9")
                process_out = self.ssh_obj.execute(command="ps -eaf | grep 'poseidonos'")
                logger.info("process_out is {}".format(str(process_out)))
                if "poseidonos" in str(process_out[1]):
                   raise Exception ("failed to kill the pos os")
                else:
                   logger.info("POS OS was stopped successfully!!!")
                   return True
            except:
                logger.error("This method failed to kill the pos os please check the log for instance where it killed")
                logger.error(traceback.format_exc())
                return False

class unvme_management(pos_management):
    def udev_install(self):
        """
        Method to run udev_install command
        return True/False
        """
        try:
            logger.info("Running udev_install command")
            cmd = "cd {} ; make udev_install ".format(self.pos_path)
            udev_install_out = self.ssh_obj.execute(cmd)
            out = ''.join(udev_install_out)
            logger.info(out)
            match = [data for data in udev_install_out if "update udev rule file" in data or "copy udev bind rule file" in data]
            if match:
               logger.info("Successfully executed the make udev_install command")
               return True
            else:
               raise Exception("failed to execute make udev_install command")
        except Exception as e:
            logger.info("command execution failed with exception  {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def construct_melloc_device(self, uram_name = 'uram0', bufer_size = '4608',  strip_size = '512'):
        """
        Method to create malloc device
        params : uram_name
               : bufer_size
               : strip_size
        return : Bool
        """
        try:
           cmd = "construct_malloc_bdev -b {} {} {}".format(uram_name, bufer_size, strip_size)
           logger.info("Running command {}".format(cmd))
           out = self.ssh_obj.execute("{}/lib/spdk/scripts/rpc.py {}".format(self.pos_path, cmd))
           return True
        except Exception as e:
           logger.error("Malloc device creation failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False

    def setup_reset(self):
        """
        method to bring Devices to kernel mode
        Return : tuple(Bool)
        """
        try:
           udev_un_ins = "cd {} ; make udev_uninstall ".format(self.pos_path)
           cmd_out = self.ssh_obj.execute(udev_un_ins)
           out = ''.join(cmd_out)
           logger.info(out)
           match = [data for data in cmd_out if "The rule file removed" in data.strip() ]
           if match:
              logger.info("Successfully executed the make udev_install command")
           else:
              logger.error("failed to execute make udev_install command")
              return False
           setup_env_cmd = self.pos_path + "/lib/%s/scripts"%self.spdk_version + "/setup.sh" + " reset"

           self.ssh_obj.execute(setup_env_cmd)
           logger.info("waiting for 5 seconds for drives to come kernel mode")
           time.sleep(3)
           cmd = "nvme list | awk '{print $1}' | grep 'nvme'"
           nvme_list = self.ssh_obj.execute(cmd)
           logger.info(nvme_list)
           if len(nvme_list[1])  != 0 :
              logger.info("Drives Brought back to kernel mode")
              return True
           else:
              raise Exception ("failed to bring Devices to kernel mode")
        except Exception as e:
              logger.error("command execution failed with exception {}".format(e))
              logger.error(traceback.format_exc())
              return False

    def scan_dev(self):
        """
        Method to scan devices
        :return: Tuple(Boolean,output)
        """
        try:
           cmd = "scan"
           out = self.run_cli_command(cmd, command_type ='device')

           if out[0]==True:
              if out[1]["status_code"] == 0:
                 return True, out[1]
              else:
                 raise Exception ("scan device command failed with status code {}".format(out[1]["status_code"]))
           else:
              raise Exception ("scan device command failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False, out[1]

    def list_dev(self):
        """
        Method to list devices
        :return: Tuple(Boolean,output,devices)
        """
        try:
          cmd = "list"
          out = self.run_cli_command(cmd, command_type='device')
          devices = []
          device_map = {}
          dev_type = {'NVRAM' : [], 'SSD' : []}
          if out[0]==True:
             if out[1]["status_code"] == 0:
                if out[1]['description'].lower() == 'no any device exists':
                    logger.info("No devices listed")
                    return True, out[1], devices, device_map, dev_type
                if "data"  in out[1]:
                   dev =  out[1]['data']["devicelist"]
                   for device in dev:
                       devices.append(device["name"])
                       dev_map = {'name': device["name"],'addr': device["addr"],'mn': device["mn"],'sn': device["sn"],'size': device["size"],'type':device["type"]}
                       if dev_map['type'] in dev_type.keys():
                          dev_type[dev_map['type']].append(dev_map['name'])
                          device_map.update({device["name"]: dev_map})

                   return True, out[1], devices, device_map, dev_type
             else:
                raise Exception ("list dev command failed with status code {}".format(out[1]["status_code"]))
          else:
             raise Exception ("list dev command failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False, None, None, None, None

class array_management(unvme_management):
    def array_reset(self):
        """
        Method to reset mbr
        :return: Tuple(Boolean,output)
        """
        try:
           cmd = "reset"
           out = self.run_cli_command(cmd, command_type ='array')

           if out[0]==True:
              if out[1]["status_code"] == 0 and out[1]['description'].lower() == "reset mbr done":
                 return True, out[1]
              else:
                 raise Exception ("array reset command failed with status code {}".format(out[1]["status_code"]))
           else:
              raise Exception ("array reset command failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False, out[1]

    def create_array(self, write_buffer, datastorage, array_name, spare=None, raid_type = 'RAID5'):
        """
        Method to create array
        :param write_buffer: write_buffer disks
        :param datastorage: datastorage disk
        :param array_name  :Name of the array
        :param spare: spare disk
        :return: Tuple(Boolean,output)
        """
        try:
         if spare:
            cmd = "create -b {} -d {} -s {} --name {} --raidtype {}".format(write_buffer, datastorage, spare, array_name, raid_type )
         else:
            cmd = "create -b {} -d {} --name {} --raidtype {}".format(write_buffer, datastorage, array_name, raid_type )
         out = self.run_cli_command(cmd, command_type = 'array')

         if out[0] == True:
            if out[1]["status_code"] == 0:
               logger.info("Successfully array {} is created".format(array_name))
               return (True, out[1])
            else:
               logger.error("array {} creation failed with status code {}".format(array_name, out[1]["status_code"]))
               return False,out[1]
         elif  not out:
            raise Exception ("No output obtained while creating array {} ! please check again".format(array_name))
         else:
            raise Exception ("Array {} creation failed".format(array_name))
        except Exception as e:
            logger.error("Command Execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False, None

    def mount_array(self, array_name):
        """
         Method to mount POS array
         :params : array_name : Name of the pos array to be mounted
        :return: Tuple(Boolean,output)
        """
        try:
          cmd="mount --name {}".format(array_name)
          out = self.run_cli_command(cmd, command_type = "array")
          if out[0] == True:
             if out[1]["status_code"] == 0:
                logger.info("Successfully pos array {} is mounted".format(array_name))
                return True, out[1]
             else:
                logger.error("mount pos array {} failed with status code {}".format(array_name, out[1]["status_code"]))
                return False, out[1]
          else:
             raise Exception ("mount pos os command failed")
        except Exception as e:
            logger.error("Command Execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False, out[1]

    def unmount_array(self,array_name):
        """
         Method to unmount POS array
         :params: array_name : Name of the pos array to be unmounted
        :return: Tuple(Boolean,output)
        """
        try:
          cmd = "unmount --name {}".format(array_name)
          out = self.run_cli_command(cmd, command_type = 'array')

          if out[0] == True:
             if  out[1]["status_code"] == 0:
                 logger.info("Successfully pos array {} is unmounted".format(array_name))
                 return True, out[1]
             else:
                logger.error("unmount pos array {} command failed with status code {}".format(array_name, out[1]["status_code"]))
                return False, out[1]
          else:
             raise Exception ("unmount pos os command failed")
        except Exception as e:
             logger.error("Command Execution failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return False, out[1]

    def delete_array(self, array_name):
        """
        Method to delete the created array
        :param: Name of the array to be deleted
        output : Tuple(bool/output)
        """
        try:
           cmd="delete --name {}".format(array_name)
           out = self.run_cli_command(cmd, command_type='array')
           if out[0] == True:
              if  out[1]["status_code"] == 0:
                  return True, out[1]
              else:
                  logger.error("delete array command failed with status code {}".format(out[1]["status_code"]))
                  return False, out[1]
           else:
              raise Exception ("delete array command failed")
        except Exception as e:
            logger.error("Command Execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False, out[1]

    def get_array_info(self, array_name):
        """
        method to get POS array status
        :param : array_name : Name of the array
        :return (Bool, dict, dict)
        """
        try:
          cmd = "info --name {}".format(array_name)
          out = self.run_cli_command(cmd, command_type='array')
          if out[0] == True:
             array_status = out[1]['data']
             if "data" in out[1].keys():
                array_state = out[1]['data']['situation']
             else:
                array_state = ""
             if out[1]["status_code"] == 0:
                logger.info("array {} status is {}".format(array_name,array_status))
                logger.info("state of the array {} is {}".format(array_name, array_state))
                return (True, out[1], array_status, array_state)
             else:
                logger.error("failed to get the array {} info with status code {}".format(array_name, out[1]["status_code"]))
                return False, out[1], array_status,array_state
          else:
             raise Exception ("array {} info  command failed ".format(array_name))
        except Exception as e:
             logger.error("Command Execution failed because of {}".format(e))
             logger.error(traceback.format_exc())
             return False,None,None,None

    def list_array_devices(self, array_name):
        """
        Method to get the list data and spare devices
        :return: Tuple(Boolean,spare_dev,data_dev,buffer_dev)
        """
        spare_dev = []
        data_dev = []
        buffer_dev = []
        try:
           cmd = "list_device --name {}".format(array_name)
           out = self.run_cli_command(cmd, command_type='array')
           if out[0]==True:
              if out[1]['output']['Response']['result']['status']['code'] == 0 :
                 flag = True
              else:
                 flag = False
           else:
               raise Exception ("list array device command execution failed")
           if flag == True:
              for dev in out[1]['data']['devicelist']:
                  if (dev['type'] == "DATA"):
                      data_dev.append(dev['name'])
                  elif (dev['type'] == "SPARE"):
                       spare_dev.append(dev['name'])
                  elif (dev['type'] == "BUFFER"):
                       buffer_dev.append(dev['name'])
                  else:
                      raise Exception ("Disk type is unknown")
           else:
              raise Exception ("failed to execute list_array_device command")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return (False, out[1])
        return (True,data_dev,spare_dev,buffer_dev)

    def list_array(self):
        """
        method to list array present and the drives used
        :return : dict{ array_name: {spare :[], data:[], uram:[],status: ''}
        """
        try:
            array_dict = {}
            cmd = "list"
            out = self.run_cli_command(cmd, command_type = 'array')
            if out[0] == True:
                out = out[1]['output']['Response']
                if 'There is no array'  in out['result']['data']['arrayList'] :
                    logger.info("No arrays present in the config")
                    return True, array_dict
                else:
                    for i in out['result']['data']['arrayList']:
                        data_drives = [j['name'].strip() for j in i['devicelist'] if j['type'] == "DATA"]
                        spare =  [j['name'].strip() for j in i['devicelist'] if j['type'] == "SPARE" ]
                        budder_d = [j['name'].strip() for j in i['devicelist'] if j['type'] == "BUFFER"]
                        status = i['status']
                        array_name = i['name']
                        array_dict[array_name] = {"data" : data_drives, "spare" : spare, "buffer" : budder_d, "status" : status}
                    logger.info("list of arrays are: {}".format(list(array_dict.keys())))
                    return True, array_dict
            else:
                raise Exception("list array command execution failed ")
        except Exception as e:
            logger.error("list array command failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False,None

class volume(array_management):
    def create_vol(self, volumename, size , array_name, iops = 0, bw = 0):
        """
         Method to create volume
        :param volumename: volumename to be created
        :param size: size of the volume
        :param : iops : iops value for the volume
        :param : bw : bandwidth value for the volume
        :param : array_name : Name of the array
        :return: Tuple(Boolean,output)
        """
        try:
          cmd=" create --name {} --size {} --maxiops {} --maxbw {} --array {} ".format(volumename, size, iops, bw, array_name)

          out = self.run_cli_command(cmd, command_type="volume")

          if out[0] == True:
             if out[1]["status_code"] == 0:
                return True, out[1]
             else:
                logger.error("create volume command failed with status code {}".format(out[1]["status_code"]))
                return False,out[1]
          else:
             raise Exception ("create volume command failed")
        except Exception as e:
            logger.error("Command Execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False,out[1]

    def update_qos(self, volumename, iops, bw, array_name):
        """
        Method to update volume QOS
        : params : volumename : Name of the volume
                 : iops : new iops value to be updated for the volume
                 : bw : new bandwidth value to be updated for the volume
                 : array_name : Name of the array
        return : Tuple(Bool, output)
        """
        try:
           cmd = "update_qos --name {} --maxiops {} --maxbw {} --array {}".format(volumename, iops, bw, array_name)
           if iops is None:
              cmd = "update_qos --name {}  --maxbw {} --array {}".format(volumename,  bw, array_name)
           if bw is None:
              cmd = "update_qos --name {} --maxiops {} --array {} ".format(volumename, iops, array_name)

           out = self.run_cli_command(cmd, command_type='volume')
           if out[0] == True:
              if out[1]["status_code"] == 0:
                logger.info("Successfully updated the qos ")
                return True, out[1]
              elif int(iops) in range(1,10) and int(bw) in range(1,10):
                   raise Exception ("QOS values not supported for iops : {} and bw : {}".format(iops, bw))
              elif isinstance(iops, int) == False  or isinstance(bw, int) == False:
                   raise Exception ('non integer values no supported as QOS params')
              else:
                 raise Exception ("failed to update the qos ")
           else:
              raise Exception("update qos execution failed with error {}".format(out[1]))
        except Exception as e:
           logger.error("command failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False,out[1]

    def delete_vol(self, volumename, array_name):
        """
        Method to delete volume
        :param volumename: volumename to be deleted
        :param array_name: Name of the array
        :return: Tuple(Boolean,output)
        """
        try:
           cmd = "delete --array {} --name {} ".format(array_name, volumename)
           out = self.run_cli_command(cmd, command_type='volume')
           if out[0] == True:
              if out[1]["status_code"] == 0:
                 logger.info("Successfully volume {} deleted".format(volumename))
                 return True, out[1]
              else:
                 raise Exception ("delete volume command failed with status code {}".format(out[1]["status_code"]))
           else:
               raise Exception ("delete volume command failed with error {}".format(out[1]))
        except Exception as e:
           logger.error("command failed with exception {}".format(e))
           return False,out[1]

    def mount_vol(self, volumename,array_name, nqn = None):
        """
        Method to mount volume
        :param volumename: name of the volume to be mounted
        :param array_name: Name of the array
        :return: Tuple(Boolean,output)
        """
        try:
          cmd="mount --name {} --array {}".format(volumename, array_name)
          if nqn:
             cmd += " --subnqn {}".format(nqn)
          out = self.run_cli_command(cmd, command_type = 'volume')
          if out[0] == True:
             if out[1]["status_code"] == 0:
                return True, out[1]
             else:
                raise Exception ("mount volume failed with status code {}".format(out[1]["status_code"]))
          else:
             raise Exception ("mount volume command failed error {} ".format(out[1]))
        except Exception as e:
           logger.error("command failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False,out[1]

    def unmount_vol(self, volumename, array_name):
        """
        Method to unmount volumes
        :param volumename: volumename to be unmounted
        :param array_name: Name of the array
        :return: Tuple(Boolean,output)
        """
        try:
           cmd="unmount --name {} --array {}".format(volumename, array_name)
           out = self.run_cli_command(cmd, command_type = 'volume')
           if out[0] == True:
              if out[1]["status_code"] == 0:
                 return True, out[1]
              else:
                 raise Exception ("unmount volume failed with status code {}".format(out[1]["status_code"]))
           else:
              raise Exception ("unmount volume command failed with error {}".format(out[1]))
        except Exception as e:
           logger.error("command failed with exception {}".format(e))
           logger.error(traceback.format_exc())
           return False,None

    def list_vol(self, array_name):
        """
        Method to list volumes
        :param : array_name: Name of the array
        :return: Tuple(Boolean,output,volumes)
        """
        try:
            vol_dict = {}
            volumes = []
            cmd = "list --array {}".format(array_name)
            out = self.run_cli_command(cmd, command_type='volume')

            if out[0] == True:
                if "data" in out[1]:
                    logger.info(out[1]['data']["volumes"])
                    if out[1]["status_code"] == 0:
                        for vol in out[1]['data']["volumes"]:
                            if vol['status'] == "Unmounted":
                               vol_dict[vol["name"]] = {"total":vol["total"],'status':vol['status'],'max_iops':vol['maxiops'],'maxbw':vol['maxbw']}
                               volumes.append({vol["name"] : {"total":vol["total"],'status':vol['status'],'max_iops':vol['maxiops'],'maxbw':vol['maxbw']}})
                            else:
                               vol_dict[vol["name"]] = {"total":vol["total"],"remain":vol["remain"],'status':vol['status'],'max_iops':vol['maxiops'],'maxbw':vol['maxbw']}
                               volumes.append({vol["name"] : {"total":vol["total"],"remain":vol["remain"],'status':vol['status'],'max_iops':vol['maxiops'],'maxbw':vol['maxbw']}})
                        if "params" in out[1].keys():
                           return True, out[1], list(vol_dict.keys()), out[1]['data']["volumes"], out[1]["params"]
                        else:
                           return True, out[1], list(vol_dict.keys()), out[1]['data']["volumes"]
                    else:
                        raise Exception ("list volume command failed with status code {}".format(out[1]["status_code"]))
                else:
                    raise Exception ("No volumes are there in the array ")
            else:
                raise Exception("list volume command execution failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False,None

    def rename_vol(self, volname, new_volname, array_name):
        """
        method to rename volume
        :param volname: old volume
        :param new_volname: new volname
        :param array_name: Name of the array
        :return: bool
        """
        try:
            logger.info("Verifying in the old volume exists")
            out = self.list_vol()
            logger.info("ouput list i s{} ".format(out[3].keys()))
            if volname not in out[3].keys():
               raise Exception("list volume failed to list the given volume {}".format(volname))

            cmd = "rename  --name {} --newname {} --array {}".format(volname, new_volname, array_name)
            out = self.run_cli_command(cmd, command_type='volume')
            vol_list = self.list_vol()
            if out[0] == True:
               if out[1]["status_code"] == 0 and str(new_volname) in vol_list[2]:
                  logger.info("volname changed from {} to {} successfully".format(volname, new_volname))
                  return True,out[1]
               else:
                  raise Exception("rename volume failed with status code {}".format(out[1]["status_code"]))
            else:
               raise Exception ("rename volume command execution failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return  False,out[1]

class wbt_management(volume):
    def wbt_parser(self,file_name):
        """
        Method :Parses WBT output files
        Parameters : file_name = name of the output file
        :return : Dict
        """
        try:
            logger.info("parsing Output")
            parse_cmd = "cat {}".format(file_name)
            out = self.ssh_obj.execute(parse_cmd)
            map_dict, temp = {}, []
            for par in out:
                if ":" in par:
                    temp = par.split(":")
                    temp_name = temp[0].lower()
                    temp_name.replace(" ", "_")
                    map_dict[temp_name] = temp[1].strip()
            return True, map_dict
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            logger.error(traceback.format_exc())
            return False, None
        
    def set_gc_threshold(self, normal , urgent, array_name):
        """
        Method to set the gc threshold values
        Parameters : urgent : normal threshold value
                    normal : urgent threshold value
        return : return : Tuple(Boolean, output)
        """
        gc_cmd = "set_gc_threshold --normal {} --urgent {} --array {} ".format(normal , urgent, array_name)
        try:
          out = self.run_cli_command(gc_cmd , command_type = "wbt")
          if out[0] == True:
             if out[1]['status_code'] == 0:
                logger.info("successfully gc threshold values are set")
                return True,out[1]
             else:
                raise Exception ("Failed to set the gc threshold value with status code {}".format(out[1]['status_code']))
          else:
             raise Exception("set_gc_threshold failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {} ".format(e))
            logger.error(traceback.format_exc())
            return (False,out[1])

    def get_gc_status(self, array_name):
        """
        Method to get the gc status
        return : return : Tuple(Boolean, output, mode)
        """
        gc_cmd = "get_gc_status --array {}".format(array_name)
        try:
            logger.info("running cli command {} ".format(gc_cmd))
            out = self.run_cli_command(gc_cmd , command_type = "wbt")
            if out[0] == True:
               if  out[1]['status_code'] == 0:
                   logger.info("successfully get_gc_status command is executed")
                   return True,out[1]['data'], out[1]['data']['gc']['status']['mode']
               else:
                   raise Exception ("get_gc_status command execution failed with status code {}".format(out[1]['status_code']))
            else:
               raise Exception ("get_gc_status command execution failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {} ".format(e))
            logger.error(traceback.format_exc())
            return (False, out[1])

    def do_gc(self, array_name):
        """
        Method to do garbage collection
        return : return : Tuple(Boolean, output)
        """
        gc_cmd = "do_gc --array {}".format(array_name)
        try:
          logger.info("running cli command {} ".format(gc_cmd))
          out = self.run_cli_command(gc_cmd , command_type = "wbt")
          if out[0] == True:
             if  out[1]['status_code'] == 0:
                 logger.info("successfully do_gc command is executed")
                 return True,out[1]
             else:
                 raise Exception ("do_gc command failed with status code {}".format(out[1]['status_code']))
          else:
             raise Exception ("do_gc command failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command failed with exception {} ".format(e))
            logger.error(traceback.format_exc())
            return (False,out[1])

    def get_gc_threshold(self,array_name):
        """
        Method to get the gc threshold
        return : return : Tuple(Boolean, output)
        """
        gc_cmd = "get_gc_threshold --array {}".format(array_name)
        try:
            logger.info("running cli command {} ".format(gc_cmd))
            out = self.run_cli_command(gc_cmd , command_type = "wbt")
            if out[0] == True:
               logger.info("Status_code={}".format(out[1]["status_code"]))
               if  out[1]['status_code'] == 0:
                   logger.info("successfully get_gc_threshold command is executed")
                   return True,out[1]['data']
               else:
                   raise Exception ("get_gc_threshold command failed with status code {} ".format(out[1]['status_code']))
            else:
               raise Exception ("get_gc_threshold command failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {} ".format(e))
            logger.error(traceback.format_exc())
            return (False, out[1])

    def wbt_flush(self,array_name):
        """
        Method to flush all user data
        :return :Tuple (Boolean,output)
        """
        flush_cmd="flush --array {}".format(array_name)
        try:
          logger.info("running cli command {} ".format(flush_cmd))
          out = self.run_cli_command(flush_cmd, command_type = "wbt")
          if out[0]==True:
             logger.info("Status_code={}".format(out[1]["status_code"]))
             if out[1]['status_code'] == 0:
                logger.info("Successfully flush command executed")
                return (True,out[1])
             else:
                raise Exception("Failed to execute flush command with status code {}".format(out[1]['status_code']))
          else:
             raise Exception("flush command execution failed with error {}".format(out[1]))
        except Exception as e:
            logger.error("command failed with exception {} ".format(e))
            return (False, out[1])

    def read_vsamap_entry(self, vol_name, rba, array_name):
        """
        Method to read vsamap entry
        : params : vol_name : Name of the volume
                 : rba : rba location
        return : Bool,Dict
        """
        try:
          logger.info("Executing read_vsamap_entry command")
          output_txt_path = self.file_gen_path

          if self.is_file_present(output_txt_path) == True:
             delete_cmd = "rm -fr {}".format(output_txt_path)
             logger.info("Deleting existing output files")
             out = self.ssh_obj.execute(delete_cmd)

          vsamap_entry_cmd = "read_vsamap_entry --name {} --rba {} --array {} ".format(vol_name, rba, array_name)
          flag_vsmap, out_vsmap = self.run_cli_command(vsamap_entry_cmd, command_type = "wbt")
          if flag_vsmap == False or  int(out_vsmap['data']['returnCode']) < 0 :
             raise Exception("Command Execution failed; Please check and Retry again")
          else:
             if self.is_file_present(output_txt_path) == False:
                raise Exception("output file not generated")
             else:
                logger.info("Output.txt file Generated!!!")
                flag_par_vsa, map_dict_par_vsa = self.wbt_parser(output_txt_path)
                if flag_par_vsa == True:
                   logger.info("Successfully data parsed from output.txt file ")
                   return True,map_dict_par_vsa
                else:
                   raise Exception("Failed to parse data from output.txt file")
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            logger.error(traceback.format_exc())
            return False,None

    def read_stripemap_entry(self, vsid, array_name):
        """
        Method to read stripe map entry
        : params : vol_name : Name of the volume
                 : vsid : vsid location
        return : Bool,Dict
        """
        try:
          logger.info("Executing read_stripemap_entry command")
          output_txt_path = self.file_gen_path

          if self.is_file_present(output_txt_path) == True:
             delete_cmd = "rm -fr {}".format(output_txt_path)
             logger.info("Deleting existing output files")
             out=self.ssh_obj.execute(delete_cmd)

          cmd = "read_stripemap_entry --vsid {} --array {}".format(vsid, array_name)
          flag_rs_map, out_rs_map = self.run_cli_command(cmd, command_type = "wbt")
          if flag_rs_map == False or  int(out_rs_map['data']['returnCode']) < 0 :
             raise Exception("Command Execution failed; Please check and Retry again")
          else:
             if self.is_file_present(output_txt_path) == False:
                raise Exception("output file not generated")
             else:
                logger.info("Output.txt file Generated!!!")
                flag_wbt_par, map_dict_wbt_par = self.wbt_parser(output_txt_path)
                if flag_wbt_par == True:
                   logger.info("successfully parsed data from output.txt file")
                   return True,map_dict_wbt_par
                else:
                   raise Exception("failed to parse data from output.txt file")
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            logger.error(traceback.format_exc())
            return False,None

    def translate_device_lba(self,array_name,logical_stripe_id=0,logical_offset=10):
        """
        Method to translate to device lba from logical stripe and logical offset
        return :Tuple (Boolean,output)
        parameters:
            logical_stripe_id: Logical stripe id
            logical_offset: logical offset
        """
        try:
           output_txt_path = self.file_gen_path
           if self.is_file_present(output_txt_path) == True:
              delete_cmd = "rm -fr {}".format(output_txt_path)
              logger.info("Deleting existing output files")

              out=self.ssh_obj.execute(delete_cmd)

           lba_cmd = "translate_device_lba --lsid {} --offset {} --name {}".format(logical_stripe_id,logical_offset,array_name)

           flag_lba, out_lba = self.run_cli_command(lba_cmd, command_type = "wbt")

           if flag_lba == False or  int(out_lba['data']['returnCode']) < 0:
              raise Exception("Command Execution failed; Please check and Retry again")
           else:
              if self.is_file_present(output_txt_path) == False:
                 raise Exception ("output file not generated")
              else:
                 logger.info("Output.txt file Generated!!!")
                 flag_par_lba, trans_dict_lba = self.wbt_parser(output_txt_path)
                 if flag_par_lba == True:
                    logger.info("Successfully data parsed from output.txt file ")
                    return True, trans_dict_lba
                 else:
                    raise Exception("failed to parse output.txt file")
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            logger.error(traceback.format_exc())
            return False,None

    def write_uncorrectable_lba(self,device_name, lba):
        """
        Method to write write_uncorrectable error to the device of specified lba
        : params : device_name : Name of the device
                 : lba : lba location
        :return: Bool
        """
        try:
          cmd = "write_uncorrectable_lba --dev {} --lba {}  ".format(device_name,lba)
          out = self.run_cli_command(cmd, command_type = "wbt")
          if out[0]==True:
             logger.info("Status_code={}".format(out[1]["status_code"]))
             if int(out[1]['data']['returnCode']) >= 0 \
                        and out[1]['description'].lower() == "pass" \
                        and out[1]['status_code'] == 0:
                logger.info("Successfully injected error to the device {} in lba {}".format(device_name,lba))
                return True
             else:
                raise Exception("Failed to inject error to the device {} in lba {} ".format(device_name, lba))
        except Exception as e:
            logger.error("command execution failed because of {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def random_File_name(self):
        """
        Method will generate 15-character
        Random string with date time
        """
        letters = string.ascii_lowercase
        Name=''.join(random.choice(letters) for i in range(15))
        datetime_object = datetime.now()
        date = (str(datetime_object).replace(' ','-')).split(".")[0].replace(":","-")

        return Name + "_" + date


    def read_raw(self, dev, lba, count):
        """
        Method : wbt command to read raw
        parameters:
                    dev : name of the device
                    lba : start lba
                    count : number of lba's to read
        return : Bool, output
        """
        try:
           file_name = "/tmp/{}.bin".format(self.random_File_name())
           wbt_cmd = "read_raw --dev {} --lba {} --count {}  --output {} ".format(dev, lba, count, file_name)
           flag, out = self.run_cli_command(wbt_cmd, command_type = "wbt")
           if flag == True and int(out['data']['returnCode']) >= 0 :
              logger.info("Successfully executed read_raw command on device  {} from lba {}".format(dev, lba))
              return True, out
           else:
              logger.error("read_raw command execution failed with return code {} ".format(out['data']['returnCode']))
              return False,None
        except Exception as e:
            logger.error("command execution failed because of  {}".format(e))
            logger.error(traceback.format_exc())
            return False,None

class detach_attach_managemnt(wbt_management):
    def dev_bdf_map(self):
        """
        Method to get the dev and bdf map
        :return: dict {devicename:bdf}
        """
        try:
           dev_bdf_map = {}
           list_dev_out = self.list_dev()
           if list_dev_out[0] == True:
              logger.info("Successfully fetched devices list")
              for dev in list_dev_out[3]:
                  dev_bdf_map[dev] = list_dev_out[3][dev]['addr']
              logger.info(dev_bdf_map)
           else:
              raise Exception ("Failed to obtain the devices list")
        except Exception as e:
            logger.error("Execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False,None
        return True,dev_bdf_map

    def device_hot_remove(self, device_list):
        """
        Method to hot plug the device
         :parameter :
            device_name : Name of the device to remove (to be passed in list)
        :return: Boolean
        """
        try:
           self.dev_addr = []
           dev_map = self.list_dev()[3]
           dev_list = ([k for k,v in dev_map.items() if {'type':'SSD'}.items() <= v.items()])
           for each_dev in device_list:
              if each_dev not in dev_list:
                 raise Exception ("given device {} is not connected to the system ".format(each_dev))
           dev_map = self.dev_bdf_map()
           if dev_map[0] == False:
              raise Exception ("failed to get the device and bdf map")
           for dev in device_list:
               pci_addr = dev_map[1][dev]
               self.dev_addr.append(pci_addr)
               logger.info("pci address {} for the given device is {} ".format(pci_addr,dev))
               hot_plug_cmd = "echo 1 > /sys/bus/pci/devices/{}/remove ".format(pci_addr)
               logger.info("Executing hot plug command {} ".format(hot_plug_cmd))
               self.ssh_obj.execute(hot_plug_cmd)
               time.sleep(2)
               list_dev_out = self.dev_bdf_map()
               if list_dev_out[0] == False:
                  raise Exception ("failed to get the device and bdf map after removing the disk")
               if pci_addr in list(list_dev_out[1].values()):
                  raise Exception ("failed to hot plug the device {} ".format(dev))
               else:
                  logger.info("Successfully removed the device {} ".format(dev))
           return True,device_list
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def device_hot_remove_by_bdf(self, bdf_addr_list):
        """
        Method to hot plug the device by bdf address
         :parameter :
            bdf_addr_list :  list of bdf addresses to remove
        :return: Boolean
        """
        try:
           self.dev_addr = bdf_addr_list
           addr_list = self.get_nvme_bdf()
           for each_addr in bdf_addr_list:
              if each_addr not in  addr_list[1]:
                 logger.error("nvme device not found with the bdf {} ".format(each_addr.strip()))
                 return False
              logger.info("removing the bdf : {}".format(each_addr))
              hot_plug_cmd = "echo 1 > /sys/bus/pci/devices/{}/remove ".format(each_addr.strip())
              logger.info("Executing hot plug command {} ".format(hot_plug_cmd))
              self.ssh_obj.execute(hot_plug_cmd)
              bdf_list = self.get_nvme_bdf()
              if bdf_list[0] == False:
                 raise Exception ("failed to get the nvme device bdf")
              if each_addr in bdf_list[1]:
                 raise Exception ("failed to hot plug the device with bdf : {} ".format(each_addr.strip()))
              else:
                 logger.info("Successfully removed the device with bdf :{} ".format(each_addr.strip()))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False
        return True

    def get_nvme_bdf(self):
        """
        Method to get the bdf address of nvme bdf
        :return: Tuple(Boolea, nvme bdf address)
        """
        try:
           logger.info("feteching the nvme device bdf")
           bdf_cmd = "lspci -D | grep 'Non-V' | awk '{print $1}'"
           bdf_out = self.ssh_obj.execute(bdf_cmd)
           logger.info("bdf's for the connected nvme drives are {} ".format(bdf_out))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False,None
        return True,bdf_out

    def pci_rescan(self):
        """
        Method to rescan the pci ports
        :return: Boolean
        """
        try:
           logger.info("Executing list dev command before rescan")
           list_dev_out_bfr_rescan = self.dev_bdf_map()
           logger.info("No. of devices before rescan: {} ".format(len(list_dev_out_bfr_rescan[1])))
           logger.info("running pci rescan command ")
           re_scan_cmd = "echo 1 > /sys/bus/pci/rescan "
           self.ssh_obj.execute(re_scan_cmd)
           logger.info("verifying whether the removed device is attached back or not")
           logger.info("scanning the devices after rescan")
           time.sleep(5) # Adding 5 sec sleep for the sys to get back in normal state
           scan_out = self.scan_dev()
           if scan_out[0] == False:
              raise Exception ("after pci rescan scan_dev command failed ")
           list_dev_out_aftr_rescan = self.dev_bdf_map()
           if list_dev_out_aftr_rescan[0] == False:
              raise Exception ("failed to get the device and bdf map after pci rescan")
           logger.info("No. of devices after rescan: {} ".format(len(list_dev_out_aftr_rescan[1])))
           if (len(list_dev_out_aftr_rescan[1])) < (len(list_dev_out_bfr_rescan)):
              raise Exception ("After rescan the removed device didn't get detected ")
        except Exception as e:
            logger.error("pci rescan command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False
        return True

    def check_rebuild_status(self, array_name):
        """
        Method to check whether rebuilding is completed or not
        :return: Bool
        """
        try:
            info_status = 0
            while (info_status <= 300):
               get_pos_status = self.get_array_info(array_name = array_name)

               if get_pos_status[0] == True and get_pos_status[2]['rebuildingProgress'] == '0' and get_pos_status[2]["situation"] == "NORMAL":
                  logger.info("rebuild status is updated in array info command")
                  break
               else:
                   info_status +=1
                   logger.info("verifying if rebuilding progress status is 0")
                   time.sleep(2)
            else:
                raise Exception ("rebuilding failed for the array {}".format(array_name))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False
        return True

    def add_spare_drive(self,device_name, array_name):
        """
        Method to remove the spare disk
        :params: device_name : Name of the device to be added
               : array_name  : Name of the array
        :return: Bool,output
        """
        try:
            cmd = "add --spare {} --array {}".format(device_name ,array_name)
            out = self.run_cli_command(cmd, command_type='array')
            if out[0]==True:
               status_code = out[1]['output']['Response']['result']['status']['code']
               if status_code == 0 :
                  logger.info("Successfully device {} is attached as spare to the array {}".format(device_name, array_name))
                  return True,out[1]
               else:
                  raise Exception ("Faled to add the device {} as spare to the array {} with status code  {}".format(device_name, array_name, status_code))
            else:
               raise Exception ("add spare drive to the array {} command failed with error {}".format(array_name, out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            return False,out[1]

    def remove_spare_drive(self,array_name, device_name):
        """
        Method to remove the spare disk
        :params: device_name : Name of the device to be removed
               : array_name : Name of the array
        :return: Bool
        """
        try:
            cmd = "remove --array {} --spare {} ".format(array_name, device_name)
            out = self.run_cli_command(cmd, command_type = "array")
            if out[0]==True:
               status_code = out[1]['output']['Response']['result']['status']['code']
               if  status_code == 0:
                   logger.info("spare device is successfully detached to the array {}".format(array_name))
                   return True
               else:
                   raise Exception ("detach spare device from the array {} command failed with status code {}".format(array_name, status_code))
            else:
               raise Exception ("detach spare device to the array {} command failed with error {}".format(array_name, out[1]))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False

class Nvmf_transport(detach_attach_managemnt):
    def get_mellanox_interface_ip(self):
       """
       Method to get the mellonx interface ip
       return dict of mellanox interface name & ip address or None if not found any interface
       """
       try:
        mlx_inter = []

        self.cnctd_mlx_inter = []

        ip_addr = {}

        cmd = "ls /sys/class/net"

        out = self.ssh_obj.execute(cmd)

        for inter in out:
            if inter.strip() != "lo":
               cmd="ethtool -i {} | grep  driver:".format(inter.strip())
               mlx_out = self.ssh_obj.execute(cmd)
               if "mlx" in str(mlx_out[0]):
                  mlx_inter.append(inter)
                  status_cmd = "cat /sys/class/net/{}/operstate".format(inter.strip())
                  port_status = self.ssh_obj.execute(status_cmd)
                  if port_status[0].strip() == "up":
                     self.cnctd_mlx_inter.append(inter.strip())

        for c_iner in  self.cnctd_mlx_inter:
                cmd = 'ifconfig {} | grep inet'.format(c_iner.strip())
                try:
                   inet_out=self.ssh_obj.execute(cmd.strip())
                   ip_address=re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',inet_out[0]).group()
                   if  ip_address:
                       ip_addr[c_iner] = ip_address
                except:
                    logger.warn("IP is not assigned to the connected mellanox interface {} ".format(c_iner.strip()))
        logger.info("Mellanox interfaces are {} ".format(mlx_inter))
        logger.info("Connected Mellanox interfaces are {} ".format(self.cnctd_mlx_inter))
        if len(list(ip_addr.values())) == 0:
           logger.error("Ip is not assigned to any of the Mellanox")
           return False, ip_addr
        else:
            return (True,ip_addr)
       except Exception as e:
            logger.error("command execution failed with exception {}" .format(e) )
            logger.error(traceback.format_exc())
            return (False, None)

    def rpc_parser_dict(self, key_name, jsonout):
        """
        Method to pass RPC output
        Params : key_name : Key type [NQN]
        """
        if '[]\n' in jsonout[0]:
         return True, {}
        out = "".join(jsonout[1:-1])
        number = len((out.split("},\n  {")))
        dict1 = {}
        if number == 0:
           return True,dict1
        if number == 1:
            dict_item=json.loads(out)
            if "product_name" in dict_item:
                dict1[dict_item['name']] = dict_item
                return True,dict1
            if "nqn" in  dict_item:

                dict1[dict_item['nqn']] = dict_item
                return True,dict1
            if  "trtype" in dict_item:
                dict1[dict_item['trtype']] = dict_item

                return True,dict1

        for i,v in enumerate((out.split("},\n  {"))):

            if i==0:
               dict_item = json.loads(v+"}")
               if "product_name" in dict_item:
                   dict1[dict_item['product_name']] = dict_item
               elif  "trtype" in dict_item:
                   dict1[dict_item['trtype']] = dict_item
               else:
                   dict1[dict_item['nqn']] = dict_item

            elif i==number-1:

               dict_item=json.loads("{"+v)
               if "product_name" in dict_item:
                   dict1[dict_item['product_name']] = dict_item
               elif  "trtype" in dict_item:
                   dict1[dict_item['trtype']] = dict_item
               else:
                   dict1[dict_item['nqn']]=dict_item

            else:

                dict_item=json.loads("{"+v+"}")
                if "product_name" in dict_item:
                    dict1[dict_item['product_name']] = dict_item
                elif  "trtype" in dict_item:
                   dict1[dict_item['trtype']] = dict_item
                else:
                    dict1[dict_item["nqn"]]=dict_item
        return True, dict1

    def generate_nqn_name(self, default_nqn_name = 'nqn.2021-05.pos'):
        """
        Method to generate random nqn name
        return nqn  name
        """
        out = self.execute_nvmf_get_subsystems()
        if out[0] is False:

            return  None
        num = len(list(out[1].keys()))
        if num is 1:
            logger.info("creating first Nvmf Subsystem")
            return  "{}:subsystem1".format(default_nqn_name)
        elif num is 0 :
            logger.error("No Subsystem information found, please verify pos status")
            return  None
        else:
            temp = list(out[1].keys())
            temp.remove('nqn.2014-08.org.nvmexpress.discovery')
            count = []
            for subsystem in temp:
                c = int(re.findall('[0-9]+', subsystem)[2])
                count.append(c)
            next_count = max(count) + 1
            new_ss_name = "{}:subsystem{}".format(default_nqn_name, next_count)
            logger.info("subsystem name is {}".format(new_ss_name))
        return   new_ss_name

    def execute_nvmf_get_subsystems(self):
        """
        method executes nvmf_get_subsystems
        return bol, output
        """
        try:
          cmd = "{}/lib/spdk/scripts/rpc.py nvmf_get_subsystems".format(self.pos_path)
          out = self.ssh_obj.execute(cmd)
          json_out = self.rpc_parser_dict('nqn', out)
          if json_out[0] is True:
             logger.info(json_out[1])
             return (True, json_out[1])
          else:
             raise Exception("Failed to parse json")
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return (False, None)

    def create_nvmf_subs(self, nqn_name, ns_count, s = "IBOF00000000000001", d = "IBOF_VOLUME"):
        """
        Method to create Nvmf Subsystem
        Input nqn name
        return Bool
        """
        try:
          command1 = "nvmf_create_subsystem {} -a -s {} -d {} -m {} ".format(nqn_name, s ,d, ns_count)
          self.ssh_obj.execute("{}/lib/spdk/scripts/rpc.py {}".format(self.pos_path,  command1))
          out = self.execute_nvmf_get_subsystems()
          if out[0] is True and nqn_name in out[1].keys():
             logger.info("Nvmf Subsystem {} created".format(nqn_name))
             return (True, out)
          else:
             raise Exception ("Failed to create Nvmf Subsystem {}".format(nqn_name))
        except Exception as e:
             logger.error("command execution failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return (False,out)

    def execute_nvmf_get_transports(self):
        """
        method executes nvmf_get_transports
        return bool, output
        """
        try:
          cmd = "{}/lib/spdk/scripts/rpc.py nvmf_get_transports".format(self.pos_path)
          out = self.ssh_obj.execute(cmd)
          json_out = self.rpc_parser_dict("trtype", out)
          if json_out[0] is True:
             logger.info("get_nvmf_get_transports output is {}".format(json_out[1]))
             return (True, json_out[1])
          else:
             raise Exception("Failed to get nvmf transports ")
        except Exception as e:
             logger.error("command execution failed with exception {}".format(e))
             logger.error(traceback.format_exc())
             return (False, json_out[1])

    def create_transport(self,buf_cache_size = 64,num_shared_buffers = 4096, transport = 'TCP'):
        """
        Method to create transport
        params:
        buf_cache_size : buffer cache size
        num_shared_buffers : Num of shared buffers
        transport: mode of transport to be used
        return True/False
        """
        try:
            command = "nvmf_create_transport -t {} -b {} -n {}".format(transport.upper(), buf_cache_size, num_shared_buffers)
            out = self.ssh_obj.execute("{}/lib/spdk/scripts/rpc.py {}".format(self.pos_path, command))
            return True
        except Exception as e:
            logger.error("command execution  failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False

    def nvmf_add_listner(self, nqn_name, mellanox_interface, port, transport = 'TCP'):
        """
        Method to create listner to nvmf ss
        Params : nqn_name > Name of SS
                 mellanox_interface : mlnx_ip
                 port details
                 Transport = RDMA/TCP
        return Bool
        """
        try:
          if transport == 'RDMA' or 'TCP' or 'tcp' or 'rdma':

             command3 = "nvmf_subsystem_add_listener {} -t {} -a {} -s {}".format(nqn_name, transport.lower(), mellanox_interface, port)

             self.ssh_obj.execute("{}/lib/spdk/scripts/rpc.py {}".format(self.pos_path, command3))
             out = self.execute_nvmf_get_transports()
             if out[0] is True and transport.upper() in out[1].keys():
                logger.info("Created Transport with {}".format(transport))
                return True
             else:
                raise Exception ("Failed to add listner to subsystem {}".format(nqn_name))
        except Exception as e:
            logger.error("command execution failed with exception {}".format(e))
            logger.error(traceback.format_exc())
            return False

class POS(Nvmf_transport):

    def __init__(self,ssh_obj,pos_path):
        
        self.ssh_obj = ssh_obj
        self.pos_path = pos_path
        self.utils_obj = Client(ssh_obj)
        self.file_gen_path = "/root/output.txt"

    def parse_out(self, jsonout, command):
        """
        Method to parse the cli command
        :param out: output of cli command
        :return: parsed dict output
        """
        out = json.loads(jsonout)
        command = out["Request"]["command"]
        if "param" in out.keys():
            param = out["Request"]["param"]
        else:
            param = {}
        status_code = out["Response"]["result"]["status"]["code"]
        description = out["Response"]["result"]["status"]["description"]
        logger.info("status code response from the command {} is {}".format(command, status_code))
        logger.info("DESCRIPTION reposonse from command {} is {}".format(command, description))

        if "data" in out["Response"]['result']:
            return {"output":out,"command":command,"status_code":status_code,"description":description,"data":out["Response"]["result"]["data"], "params": param}
        else:
            return {"output": out, "command": command, "status_code": status_code, "description": description,"params": param}

    def run_cli_command(self,command, command_type):
        """
        Method to run pos cli commands
        :param command: command to be executed
        :return: Tuple(Boolean,output)
        """
        try:
            start_time = time.time()
            out = self.ssh_obj.execute("{}/bin/cli {}  --json  {}".format(self.pos_path,command_type, command), get_pty = True)
            elapsed_time_secs = time.time() - start_time
            logger.info("command execution completed in  : {} secs ".format(timedelta(seconds=elapsed_time_secs)))
            out = "".join(out)
            logger.info("Raw output of the command {} is {}" .format(command , out))
            if "iBoF Connection Error"  in out:
                logger.warning("iBOF os is not running! please start iBOF and try again!")
                return False,out
            elif "invalid data metric" in out:
                logger.warning("invalid syntax passed to the command ")
                return False,out
            elif "invalid json file" in out:
                 logger.error("passed file contains invalid json data")
                 return False,out
            elif "Receiving error" in out:
                 logger.error("pos os crashed in between ! please check pos logs")
                 return False,out
            else:
                parse_out = self.parse_out(out, command)
                return True,parse_out
        except Exception as e:
            logger.error("Command Execution failed because of {}".format(e))
            return False, None
