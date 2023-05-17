import os, glob, subprocess, sys, argparse
from datetime import datetime

now = datetime.now()
current_time = now.strftime("%H_%M")

passed_file_name = "passed_results_{}.log".format(current_time)
failed_file_name = "failed_error_result_{}.log".format(current_time)


def __run_command__(cmd):
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    out = ""
    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline()
        nextline = nextline.decode("utf-8")

        if "passed" in nextline or "failed" in nextline:
            break
        elif nextline == "" and process.poll() is not None:
            break
        else:
            out += nextline + "\n"

        sys.stdout.write(nextline)
        sys.stdout.flush()

    return out


def read_data(loc):
    """method to read Txt document"""
    temp = {}
    try:
        with open(loc, "r") as fd:
            for line in fd:
                if "driverfile,testcasename" in line:
                    pass
                else:
                    line = line.strip()
                    line = line.split("::")
                    temp[line[1]] = line[0]
        fd.close()
        print("Running tests on {} driver files".format(len(temp.keys())))
        return temp
    except Exception as e:
        print("Reading input file failed due to {} ".format(e))
        sys.exit(0)


def execute_TCs_now(temp):
    """executes all the test cases in the dict"""
    for tc in list(temp.keys()):
        tcdata = "{}::{}".format(temp[tc], tc)
        exec_command = base_cmd + tcdata
        print("Executing command {}......".format(exec_command))
        out = __run_command__(exec_command)
        verify_results(out)
        logfile_name = temp[tc] + "_" + tc
        log = get_log(loc, logfile_name)
        print("The logs dir for {} is {}".format(tcdata, log))
        print(
            "******************************************************************************************************************"
        )


def execute_driverfiles_now(temp):
    """executes all the entire driver files in the dict"""
    for driverfile in list(temp.keys()):
        tcdata = "{}".format(driverfile)
        exec_command = base_cmd + tcdata
        print("Executing command {}......".format(exec_command))
        out = __run_command__(exec_command)
        verify_results(out)

    logfile_name = "{}_full_logs".format(driverfile.strip(".py"))
    log = get_log(loc, logfile_name)
    print("The logs dir for {} is {}".format(tcdata, log))
    print(
        "******************************************************************************************************************"
    )


def make_bash_TCs(temp):
    """makes a bash file to run the Tcs"""
    filename = "ibot_pytest_runner_TCs.sh"
    if os.path.exists(filename):
        delete_cmd = "rm -fr {}".format(filename)
        __run_command__(delete_cmd)
    with open(filename, "w") as fd:
        for i in list(temp.keys()):
            line = base_cmd + "{}::{}\n".format(i, temp[i])
            fd.write(line)
    fd.close()


def make_bash_driver_files(temp):
    """makes a bash file to run the entire driver files"""
    filename = "ibot_pytest_runner_driver_files.sh"
    if os.path.exists(filename):
        delete_cmd = "rm -fr {}".format(filename)
        __run_command__(delete_cmd)
    with open(filename, "w") as fd:
        for i in list(temp.keys()):
            line = base_cmd + "{}\n".format(i)
            fd.write(line)
    fd.close()


def get_log(loc, logfile_name):
    temp = loc.split("testcase")[0] + "logs/*"
    list_of_files = glob.glob(temp)
    # out = __run_command__("ls -ltr /root/ibof_automation/ibot/logs/")
    # print(list(out))

    latest_file = max(list_of_files, key=os.path.getctime)
    now = datetime.now()
    current_time = now.strftime("%H_%M_%S")
    new_file_name = (
        loc.split("testcase")[0] + "logs/" + logfile_name + "_" + current_time
    )
    mv_command = "mv {} {}".format(latest_file, new_file_name)
    __run_command__(mv_command)
    return new_file_name


def verify_results(
    out, passed_file_name=passed_file_name, failed_file_name=failed_file_name
):
    """method to verify execution results"""
    filename = "temp.log"
    if os.path.exists(filename):
        delete_cmd = "rm -fr {}".format(filename)
        __run_command__(delete_cmd)
    f = open(filename, "w+")
    # out = out.decode("utf-8")
    f.write(out)
    f.seek(0)
    passed, failed, errored = [], [], []

    for i in f:
        if "PASSED" in i and "::" in i and "%]" in i:
            passed.append(i)
        elif "FAILED" in i and "::" and "%]" in i:
            failed.append(i)
            return
        elif "ERROR" in i and "::" in i and "%]" in i:
            errored.append(i)
            return
    f.close()
    delete_cmd = "rm -fr {}".format(filename)
    __run_command__(delete_cmd)

    fn = open(passed_file_name, "a+")
    if len(passed) != 0:
        for i in passed:
            temp = i.split("PASSED")[0]
            fn.write("{}\n".format(temp))

    fd = open(failed_file_name, "a+")
    if len(failed) != 0:
        for i in failed:
            fd.write("{}\n".format(i.split("FAILED")[0]))
    if len(errored) != 0:
        for i in errored:
            fd.write("{}\n".format(i.split("ERROR")[0]))
    fn.close()
    fd.close()


parser = argparse.ArgumentParser(description="Process Commandline arguments.")

parser.add_argument(
    "--mul_tcs",
    dest="mul_tcs",
    action="store_true",
    help="Enable scripts to execute specific TCs from multiple driver files as mentioned in the input file",
)
parser.add_argument(
    "--mul_driver",
    dest="mul_driver",
    action="store_true",
    help="Enable scripts to execute driver files mentioned in the input file",
)
parser.add_argument(
    "--make_driver_bash",
    dest="make_driver_bash",
    action="store_true",
    help="makes bashfile to run entire driver file",
)
parser.add_argument(
    "--make_tcs_bash",
    dest="make_tcs_bash",
    action="store_true",
    help="makes bashfile to run Tcs as mentioned in the input file",
)
parser.add_argument(
    "--input_loc", dest="loc", action="store", help="location of the input file"
)

parser.add_argument(
    "--pytest_params",
    dest="pytest_parms",
    action="store",
    help='string for pytest execution eg. to skip a Tc add params as "not <marker>" eg to execute only reboot markers from a driver file add "reboot" if reboot TCs needs to be skipped from the file add "not reboot',
)

args = parser.parse_args()

base_cmd = "python3 -m pytest -v  "
if not args.loc:
    print("input file location not mentioned")
    sys.exit(1)
else:
    loc = args.loc

if args.pytest_parms:
    print("Adding pytest params to execution command")
    base_cmd += '-m "{}" '.format(args.pytest_parms)

if not (
    any([args.mul_tcs, args.mul_driver, args.make_driver_bash, args.make_tcs_bash])
):
    print("Try help for options\n")

    sys.exit(0)

tc_dict = read_data(args.loc)
print(tc_dict)

if args.make_driver_bash:
    print("creating bash files with driver info")
    make_bash_driver_files(tc_dict)

if args.make_tcs_bash:
    print("creating bash files with TCs info as mentioned in the input file")
    make_bash_TCs(tc_dict)

if args.mul_tcs:
    print("executing TCs from multiple driver files as mentioned in the input file")
    execute_TCs_now(tc_dict)

if args.mul_driver:
    print("executing all TCs from the driver files mentioned in the input file")
    execute_driverfiles_now(tc_dict)
