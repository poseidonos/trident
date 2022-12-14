import re
import paramiko
import socket
from time import sleep
from proc import Proc
import logger
import logger as logger_obj


logger = logger.get_logger(__name__)
import sys


class ConnectError(Exception):
    """connection error"""

    pass


class TimeOutError(ConnectError):
    """timeout error"""

    pass


class NotAuthorizedError(ConnectError):
    """not authorized error"""

    pass


class UnknownHostError(ConnectError):
    """host unknown error"""

    pass


class ExecuteError(Exception):
    """execution error"""

    pass


def connect(hostname, username, password, timeout, set_missing_host_key_policy=False):
    """

    :param hostname: hostname of client
    :param username: username of client
    :param password: password of client
    :param timeout: ssh timeout interval
    :param set_missing_host_key_policy: True or False
    :return: ssh connection

    Method: method to connect to remote host
    usage:

    Called internally  by SSHclient class during object initialization phase

    """

    try:
        ssh = paramiko.SSHClient()

        if set_missing_host_key_policy:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        logger.debug("attempting to connect to: {}".format(hostname))
        ssh.connect(hostname, username=username, password=password, timeout=timeout)
        logger.debug("successfully connected to: {}".format(hostname))
        return ssh

    except socket.timeout:
        message = "error connecting to: {} timed out after {} seconds".format(
            hostname, timeout
        )
        raise TimeOutError(message)

    except socket.gaierror:
        message = "error connecting to: {} host is unknown".format(hostname)
        raise UnknownHostError(message)

    except paramiko.ssh_exception.AuthenticationException:
        message = "error connecting to: {} authentication error for user {} credentials".format(
            hostname, username
        )
        raise NotAuthorizedError(message)

    except paramiko.ssh_exception.SSHException as exception:
        message = "error connecting to: {} : {}".format(hostname, str(exception))
        raise ConnectError(message)


def check_success_responses(contents, success_responses):
    """

    :param contents: output content
    :param success_responses: response in which content to be verfied
    :return: returns True if any success response in contents False otherwise
    Method: To check the response is valid or not

    Called Internally  by execute method and invoke_shell

    """
    for success_response in success_responses:
        if "{regex}" in str(success_response):
            success_response_split = success_response.split("{regex}")
            match = success_response_split[1]
            logger.debug("checking regex {} in contents".format(match))
            if re.search(match, contents, re.DOTALL):
                logger.debug("regex {} found in contents".format(match))
                return True
        else:
            if str(success_response) in contents:
                logger.debug(
                    "success response {} found in contents".format(success_response)
                )
                return True
    return False


def _shell_receive(shell, lines):
    """

    :param shell: shell object
    :param lines: output lines
    :return: return data received from shell and data to lines

    intenal methd to  receive data from channel

    """
    while not shell.recv_ready():
        sleep(0.1)

    data = ""
    while shell.recv_ready():

        data += (shell.recv(16348)).decode("UTF-8")
        # data +=(shell.recv(16348))
        # logger.info("data = {}".format(data))
    lines += re.split('["\r","\n","\t"]', data)

    return lines


class SSHclient(object):

    """
    SSH object to connect to remote host and run commands
    """

    def __init__(
        self,
        hostname,
        username,
        password,
        set_missing_host_key_policy=True,
        timeout=None,
    ):
        """

        :param hostname: hostname of client
        :param username: username of client
        :param password: password of client
        :param timeout: ssh timeout interval
        """
        logger.debug("SSHclient constructor")
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        if not timeout:
            timeout = 10

        self.ssh = connect(
            self.hostname,
            self.username,
            self.password,
            timeout,
            set_missing_host_key_policy=set_missing_host_key_policy,
        )

    def execute(
        self,
        command,
        success_responses=None,
        expected_exit_code=None,
        get_pty=False,
        m_type=None,
    ):
        """
        :param command: command to be executed
        :param success_responses: response in content to be verified
        :param expected_exit_code: int value
        :return: execution output

        Method: To execute remote command via ssh

        Usage:
        c1=SSHClient(hostname,username,password)
        c1.execute(command)
        """
        if not expected_exit_code:
            expected_exit_code = 0
        logger.debug('Executing Command "{}" on host {}'.format(command, self.hostname))
        if get_pty == True:
            stdin, stdout, stderr = self.ssh.exec_command(command, get_pty=True)
        else:
            stdin, stdout, stderr = self.ssh.exec_command(command)

        stdoutlines = stdout.readlines()
        stdout_contents = "".join(line.strip("\n\r\t") for line in stdoutlines)
        # logger.debug('\r\n{}'.format(stdout_contents))
        # logger.debug(stdoutlines)
        if success_responses:
            logger.info(
                'checking stdout for success responses "{}"'.format(success_responses)
            )
            if check_success_responses(stdout_contents, success_responses):
                return stdoutlines

            raise ExecuteError("success responses not found in stdout")

        exit_code = stdout.channel.recv_exit_status()
        logger.debug(
            "expected_exit_code is {} and  current exit code is {}".format(
                expected_exit_code, exit_code
            )
        )
        if exit_code != expected_exit_code:
            error = stderr.readlines(), "exit code: {}".format(exit_code)
            return error

        return stdoutlines

    def shell_execute(
        self, command, send_inputs, wait=0, success_responses=None, expected_code=True
    ):
        """

        :param command: command to be executed
        :param send_input: input to stdin
        :param success_responses: response in content to be verified
        :return:

        Method: to run interactive shell commands

        usage:
        c1=SSHClient(hostname,username,password)
        c1.shell_execute(command,send_inputs)

        """
        stdoutlines = []
        logger.debug(
            'executing shell command "{}" on host {}'.format(command, self.hostname)
        )

        shell = self.ssh.invoke_shell()
        _shell_receive(shell, stdoutlines)

        shell.send(command + "\n")
        _shell_receive(shell, stdoutlines)

        for send_input in send_inputs:
            shell.send(send_input + "\n")
            sleep(wait)
            _shell_receive(shell, stdoutlines)
            sleep(wait)
        #        logger.info("Exit code status ={}".format(shell.recv_exit_status()))i

        shell.close()

        stdout_contents = "".join(line.strip("\n\r\t") for line in stdoutlines)

        if success_responses:
            logger.debug(
                'checking stdout for success responses "{}"'.format(success_responses)
            )
            if check_success_responses(stdout_contents, success_responses):
                return stdoutlines

            raise ExecuteError("success responses not found in stdout")

        return stdoutlines

    def file_transfer(self, src, destination, move_to_local="yes"):
        """

        :param src: src file
        :param destination: destination file
        :param move to local  if set true will move file from   remote system to local  aotherwise vice versa
        return: True or False

        Method ; to move file from server to cleint and vice versa

        usage;
        c1=SSHClient(hostname,username,password)
        c1.file_transfer(src,destination)

        """
        logger.info("move_local_flag={}".format(move_to_local))
        if move_to_local == "yes":
            try:
                sftp = self.ssh.open_sftp()
                sftp.get(src, destination)
                logger.info(
                    "{} file moved sucessfully from  destination  to source ".format(
                        src
                    )
                )
                return True
            except Exception as e:
                logger.info("test move to local")
                logger.error("Error moving file because of {}".format(e))
                return False
            finally:
                sftp.close()
        else:
            try:
                sftp = self.ssh.open_sftp()
                sftp.put(src, destination)
                logger.info(
                    "{} file moved sucessfully from source to destination system ".format(
                        src
                    )
                )
                return True
            except Exception as e:
                logger.info("test move to  destination")
                logger.error("Error moving file because of {}".format(e))
                return False
            finally:
                sftp.close()

    def run_async(self, cmd):
        """
        :param: cmd: command to be executed
        Allows for asynchronous execution of commands
        RETURNS : A Proc object

        Usage:
        c1=SSHClient(hostname,username,password)
        c1.run_async(cmd)
        """

        logger.info("Creating a new async process for : \n" + cmd)

        # Create a new channel and set it to non-blocking mode
        channel = self.ssh.get_transport().open_session()

        # Force remote process to run on a controlling terminal by
        # forcing a pseudo-tty allocation. This way we can tie the
        # lifetime of the process to that of the terminal and not
        # leave zombie processes lying around for init to cleanup
        channel.get_pty()

        channel.setblocking(0)
        channel.exec_command(cmd)

        process = Proc(channel=channel)

        return process

    def get_node_status(self):

        """

        :return: True/False

        Method: To get remote node status

        Usage:
        c1=SSHClient(hostname,username,password)
        c1.get_node_status()
        """
        try:
            self.ssh.exec_command("ls", timeout=5)
            logger.info("Node is active")
            return True
        except Exception as e:
            logger.info("Node is inactive")
            return False

    def close(self):
        """

        :return: None

        Method: To close SSH connection

        Usage:
        c1=SSHClient(hostname,username,password)
        c1.close()
        """
        try:
            self.ssh.close()
            logger.info("ssh connection close")
        except Exception as e:
            logger.error("ssh connection close failed")


"""
if __name__=="__main__":
    logger.info("==========================================Testing execute method===================================================")
    ssh_obj = SSHclient("192.168.56.103", 'test', 'srib@123')
    out=ssh_obj.execute("ls")

    if "Music\n" in out:
        logger.info("Execute method passed")
    else:
        logger.info("Execute Method failed")

    logger.info("==========================================Testing shell execute method===================================================")


    shell_out=ssh_obj.shell_execute(command="sudo ls", send_inputs=["srib@123"])
    for x in shell_out:
        if "Music" in x:
            logger.info("Shell Execute method passed")
            break

    else:
        logger.info("shell Execute Method failed")


    logger.info("==========================================Testing run async method===================================================")

    process1 = ssh_obj.run_async("mpstat 3 12")
    out=process1.get_output()
    logger.info("out")
    process1.terminate()

    logger.info("==========================================Testing file transfer method===================================================")

    out=ssh_obj.file_transfer("node.py", "/home/test/node.py",move_to_local="no")
    if out==True:
        logger.info("file transfer  method passed")
    else:
        logger.info("File transfer Method failed")

    logger.info("==========================================Testing  get node status  method===================================================")

    out=ssh_obj.get_node_status()
    if out == True:
        logger.info("get node status  method passed")
    else:
        logger.info("get node status method failed")

"""
