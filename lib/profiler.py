
from node import SSHclient
import logger
import logger  as logger_obj
import time
import datetime
logger= logger.get_logger(__name__)





import threading

class ProfilerThread(threading.Thread):

    """
    Purpose of class:
    ProfilerThread class having methods for running and killing background stats collection task
    """
    def __init__(self, ssh_obj,sleep_interval=5):
        """

        :param ssh_obj: ssh_object where remote execution  needs to be done
        :param sleep_interval: Sleep interval in between stats collection
        """
        super(ProfilerThread,self).__init__()
        self._kill = threading.Event()
        self._interval = sleep_interval
        self.ssh_obj=ssh_obj
        self.profiler_log_path = logger_obj.get_logpath()
        self.profiler_log = self.profiler_log_path + "/profiler.log"

    def run(self):
        """

        :return: None
        Method: to start the stats collection work

        Usage:
        c1= ProfilerThread(ssh_obj)
        c1.start()
        Note: Call start method instead of run as start method internally will be calling run method

        """
        while True:

            cpu_output = self.ssh_obj.execute("mpstat ")
            disk_output = self.ssh_obj.execute("iostat ")
            mem_output = self.ssh_obj.execute("free -m")
            with open(self.profiler_log, "a+") as  log_handler:
                log_handler.write("{}=============={}===============\n".format(str(datetime.datetime.now()),"Disk_usage"))
                for lines in disk_output:
                    log_handler.write(lines)

                log_handler.write("{}=============={}===============\n".format(str(datetime.datetime.now()), "cpu_usage"))
                for lines in cpu_output:
                    log_handler.write(lines)

                log_handler.write("{}=============={}===============\n".format(str(datetime.datetime.now()), "Mem_usage"))
                for lines in mem_output:
                    log_handler.write(lines)
            is_killed = self._kill.wait(self._interval)
            if is_killed:
                break



    def kill(self):

        """

        :return:None
        method: To kill background stats collection task

        Usage:
        c1= ProfilerThread(ssh_obj)
        c1.kill()


        """
        self._kill.set()

"""
if __name__=="__main__":
    logger.info("======================================Test profiler method===========================================")
    c1 = SSHclient("192.168.56.103", "test", "srib@123")
    z1 = ProfilerThread(c1)
    z1.start()
    time.sleep(10)
    z1.kill()

"""