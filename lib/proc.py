"""
BSD LICENSE

Copyright (c) 2021 Samsung Electronics Corporation
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.
  * Neither the name of Samsung Electronics Corporation nor the names of
    its contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import re
import time
import logger


log = logger.get_logger(__name__)


class ExecutionError(RuntimeError):
    """Exception to signify an execution error"""

    pass


class TimeOutError(ExecutionError):
    """Exception to signify a time-out on the CLI"""

    pass


class Proc(object):
    """This class enables one to keep track of an async process,
    monitor its status and read the output later
    NOTE : An instance of this class is meant to run just one process,
    to run another processes, create another instance of Proc
    ** If the expected output is very large then the buf size needs
    to be adjusted appropriately. If memory is of concern, then it is
    necessary to redirect the output to a file
    """

    def __init__(self, channel):
        """Initialization code.
        channe: session over which command to be executed
        """

        self.channel = channel

    def is_complete(self):
        """Checks if the process has completed execution
        RETURNS : True / False
        usage:
        c1=Proc(channel)
        c1.is_comlete()

        """
        return self.channel.exit_status_ready()

    def terminate(self):
        """Terminates the process and closes the interface
         c1=Proc(channel)
        c1.terminate()

        """
        self.channel.close()

    def wait_for_completion(self, sleep=3, tolerance=200):
        """Polls until the completion of the process. Raises
        a TimeOutError exception if it times out.
        Returns : None
        *Note : This is a blocking call
         c1=Proc(channel)
        c1.wait_for_completion()
        """
        attempts = 0
        while not self.is_complete() and attempts < tolerance:
            time.sleep(sleep)
            attempts += 1

        if attempts >= tolerance:
            raise TimeOutError("Timed out waiting for the process to complete")

    # TODO : Add support for large output
    def get_output(self):
        """Gets the output from the command executed
        RETURNS : String

        Usage:
         c1=Proc(channel)
        c1.get_output()
        """
        buf = b""
        while self.channel.recv_ready():
            buf = self.channel.recv(6024)

        return buf
