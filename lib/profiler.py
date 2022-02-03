#
#   BSD LICENSE
#   Copyright (c) 2021 Samsung Electronics Corporation
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions
#   are met:
#   
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#        the documentation and/or other materials provided with the
#        distribution.
#      * Neither the name of Samsung Electronics Corporation nor the names of
#        its contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.
#    
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 

from node import SSHclient
import logger
import logger as logger_obj
import time
import datetime

logger = logger.get_logger(__name__)


import threading


class ProfilerThread(threading.Thread):

    """
    Purpose of class:
    ProfilerThread class having methods for running and killing background stats collection task
    """

    def __init__(self, ssh_obj, sleep_interval=5):
        """

        :param ssh_obj: ssh_object where remote execution  needs to be done
        :param sleep_interval: Sleep interval in between stats collection
        """
        super(ProfilerThread, self).__init__()
        self._kill = threading.Event()
        self._interval = sleep_interval
        self.ssh_obj = ssh_obj
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
            with open(self.profiler_log, "a+") as log_handler:
                log_handler.write(
                    "{}=============={}===============\n".format(
                        str(datetime.datetime.now()), "Disk_usage"
                    )
                )
                for lines in disk_output:
                    log_handler.write(lines)

                log_handler.write(
                    "{}=============={}===============\n".format(
                        str(datetime.datetime.now()), "cpu_usage"
                    )
                )
                for lines in cpu_output:
                    log_handler.write(lines)

                log_handler.write(
                    "{}=============={}===============\n".format(
                        str(datetime.datetime.now()), "Mem_usage"
                    )
                )
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
