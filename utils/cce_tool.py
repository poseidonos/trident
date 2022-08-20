from bs4 import BeautifulSoup
import subprocess
from re import S
import csv
from calendar import c
from collections import OrderedDict
from datetime import datetime
import json
import logger
from node import SSHclient
from ast import parse
import sys
import os
import mysql.connector as mysql

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../lib")))


logger = logger.get_logger(__name__)


class Target(object):
    def __init__(self) -> None:
        self.ssh_obj = None
        self.source_path = None
        self.lcov_path = None
        self.coverage_data = OrderedDict()         # test_name: file_name
        self.pre_coverage_varified = False
        pass

    def connect(self, ip_addr, user, password, force=False):
        self.ip_addr = ip_addr
        self.user = user
        self.passwrod = password
        try:
            ssh_obj = SSHclient(self.ip_addr, self.user, self.passwrod)
            self.set_connection(ssh_obj)
        except Exception as e:
            logger.error(f"Failed to setup SSH connection due to '{e}'")
            return False
        return True

    def set_connection(self, ssh_obj) -> None:
        if self.ssh_obj:
            logger.warning("Target old SSH connection object stil active")

        logger.info("Target SSH connection object set")
        self.ssh_obj = ssh_obj

    def get_connection(self) -> object:
        if not self.ssh_obj:
            logger.warning("Target SSH Connection is set.")
        return self.ssh_obj

    def execute(self, command):
        if not self.ssh_obj:
            logger.info("Connection object is not set")
        return self.ssh_obj.execute(command)

    def _verify_file_esists(self, path, dir_file=False):
        pre_cmd = "if test -{} {} ; then echo 'file_exist'; fi"
        if dir_file:
            command = pre_cmd.format('d', path)
        else:
            command = pre_cmd.format('f', path)

        out = " ".join(self.execute(command))
        return "file_exist" in out

    def set_source_path(self, path):
        if not self._verify_file_esists(path, dir_file=True):
            logger.error("Source path does not exist")
            return False

        self.source_path = path
        logger.info(f"Source path is set to {self.source_path}")

        return True

    def get_source_path(self):
        if not self.source_path:
            logger.warning(f"Source path is not set.")

        return self.source_path

    def set_lcov_path(self, path):
        if not self._verify_file_esists(path):
            logger.error("Lcov path does not exist")
            return False

        self.lcov_path = path
        logger.info(f"Lcov path is set to {self.lcov_path}")

        return True

    def get_lcov_path(self):
        if not self.lcov_path:
            logger.warning(f"Lcov path is not set.")

        return self.lcov_path

    def verify_coverage_pre(self, source_path=None, lcov_path=None) -> bool:

        source_path = source_path or self.get_source_path()
        if not source_path:
            logger.error("Source path is not set. Please set Source path.")
            return False

        # Verify code is compiled with gcov
        command = f"find {source_path} -name *.gcno"
        cmd_out = self.execute(command)
        if len(cmd_out) == 0:
            logger.error(
                "Coverage is not enabled. Compile POS by enabling gcov.")
            return False

        command = f"find {source_path} -name *.gcda"
        cmd_out = self.execute(command)
        if len(cmd_out) == 0:
            logger.error(
                "Coverage is not enabled. Compile POS by enabling gcov.")
            return False

        lcov_path = lcov_path or self.get_lcov_path()
        if not lcov_path:
            logger.error("Lcov path is not set. Please set locv path.")
            return False

        self.pre_coverage_varified = True
        return True

    def _init_coverage_info(self, test_id, unique_key=None):
        test_id = test_id.upper()
        if not unique_key:
            unique_key = datetime.now().strftime('%Y%m%d_%H%M%S')

        coverage_dict = {}

        lcov_file_name = f"coverage_{test_id}_{unique_key}.lcov"
        lcov_overall_file_name = "overall_coverage.lcov"

        coverage_dir_name = f"coverage_{test_id}_{unique_key}"
        coverage_overall_dir_name = "overall_coverage"

        coverage_dict["unique_key"] = unique_key
        coverage_dict["lcov_file"] = lcov_file_name
        coverage_dict["lcov_overall_file"] = lcov_overall_file_name
        coverage_dict["coverage_dir"] = coverage_dir_name
        coverage_dict["coverage_overall_dir"] = coverage_overall_dir_name
        coverage_dict["coverage_generated"] = False
        coverage_dict["html_generated"] = False
        coverage_dict["file_transfered"] = False
        coverage_dict["file_deleted"] = False

        self.coverage_data[test_id] = coverage_dict

    def get_coverage_data_dict(self, test_id):
        return self.coverage_data.get(test_id, None)

    def generate_coverage(self, test_id, unique_key=None):
        if not self.pre_coverage_varified:
            if not self.verify_coverage_pre():
                logger.error("Target code coverage setup ready.")
                return False

        self._init_coverage_info(test_id, unique_key=unique_key)
        coverage_dict = self.get_coverage_data_dict(test_id)

        cc_out = coverage_dict["lcov_file"]

        ignore_str = '"/usr/*" "*/ibofos/lib/*"'
        lcov_comds = [f'lcov -c -d src/ --rc lcov_branch_coverage=1 -o {cc_out}',
                      f'lcov --rc lcov_branch_coverage=1 -r {cc_out} {ignore_str} -o {cc_out}']
        try:
            for lcov_cmd in lcov_comds:
                cd_cmd = f"cd {self.get_pos_path()}"
                data_out = self.execute(f"{cd_cmd}; {lcov_cmd}")

            self.over_all_data = "".join(data_out[-3:])

            logger.info(f"Overall coverage data : {self.over_all_data}")
        except Exception as e:
            logger.error("Failed to get the coverage report due to '{e}.")
            return False

        # Update the code
        coverage_dict["coverage_generated"] = True
        return True

    def generate_html_report(self, test_id):
        test_id = test_id.upper()
        coverage_dict = self.get_coverage_data_dict(test_id)
        if not coverage_dict:
            logger.error(
                "Jira ID does not exist. Generate the code coverage first.")
            return False

        if not coverage_dict["coverage_generated"]:
            logger.error(
                "Coverage is not generated. Get the code coverage first.")
            return False

        lcov_out_file = coverage_dict['lcov_file']
        lcov_overall_file = coverage_dict['lcov_overall_file']

        coverage_dir = coverage_dict['coverage_dir']
        coverage_overall_dir = coverage_dict['coverage_overall_dir']

        cmd_list = [
            f"genhtml --demangle-cpp --branch-coverage {lcov_out_file} -o {coverage_dir}",
            f"cat {lcov_out_file} >> {lcov_overall_file}",
            f"genhtml --demangle-cpp --branch-coverage {lcov_overall_file} -o {coverage_overall_dir}",
        ]

        source_path = self.get_source_path()
        for cmd in cmd_list:
            command = f"cd {source_path}; {cmd}"
            self.execute(command=command)

        # Verify Files are generated
        file_path = f"{source_path}/{coverage_dir}"
        if not self._verify_file_esists(file_path, dir_file=True):
            logger.error("Html files are not generated.")
            return False

        coverage_dict["html_generated"] = True
        return True

    def fetch_coverage_report(self, test_id, source=None, destination=None):
        test_id = test_id.upper()
        coverage_dict = self.get_coverage_data_dict(test_id)
        if not coverage_dict:
            logger.error(
                "Jira ID does not exist. Generate the code coverage first.")
            return False

        if not coverage_dict["html_generated"]:
            logger.error(
                "Coverage report is not generated. Get the code coverage.")
            return False

        coverage_dir = coverage_dict["coverage_dir"]
        coverage_overall_dir = coverage_dict["coverage_overall_dir"]

        source_path = source or self.get_source_path()
        destination = destination or "/tmp"

        coverage_paths = [coverage_dir, coverage_overall_dir]
        for coverage_path in coverage_paths:
            coverage_abs_path = f"{source_path}/{coverage_path}"
            tar_path = f"{coverage_abs_path}.tar.gz"
            command = f"tar -cvzf {tar_path} {coverage_abs_path}"
            self.ssh_obj.execute(command)

            if not self._verify_file_esists(tar_path):
                logger.error(
                    f"Failed to create the coverage tar file {tar_path}.")
                return False

            dest = f"{destination}/{coverage_path}.tar"

            try:
                self.ssh_obj.file_transfer(src=tar_path, destination=dest)
            except Exception as e:
                logger.error("Failed to transefer the tar file.")
                return False

        coverage_dict["file_transfered"] = True
        return True

    def _clear_coverage(self, lcov_file):
        source = self.get_source_path()
        if not self._verify_file_esists(lcov_file):
            logger.error("File {file_name} does not exist")
            return False

        command = f"cd {source};lcov -z -d src/ --rc lcov_branch_coverage=1 -o {lcov_file}"
        self.execute(command=command)
        return True

    def _delete_file(self, file_name, dir_file=False, force=False, abs_path=False):
        if not self._verify_file_esists(file_name, dir_file=dir_file):
            logger.warning(f"File {file_name} does not exist")

        if not abs_path:
            source_dir = self.get_pos_path()
            file_name = f"{source_dir}/{file_name}"

        command = f"rm {file_name}"

        if dir_file:
            command = f"rm -r {file_name}"

        if force:
            command += " -f"

        out = self.execute(command=command)
        if out:
            logger.error(f"Failed to delete'{file_name}' due to {out}")
            return False

        return True

    def delete_coverage_files(self, test_id, all_files=False):
        test_id = test_id.upper()
        coverage_dict = self.coverage_data.get(test_id, None)
        if not coverage_dict:
            logger.error(
                "Jira ID does not exist. Generate the code coverage first.")
            return False

        if not coverage_dict["file_transfered"]:
            logger.warning(
                "Coverage report is not copied to host system. Copy before deleteing")
            return False

        lcov_out_file = coverage_dict['lcov_file']
        lcov_overall_file = coverage_dict['lcov_overall_file']
        coverage_dir = coverage_dict["coverage_dir"]
        coverage_overall_dir = coverage_dict["coverage_overall_dir"]

        self._clear_coverage(lcov_out_file)
        self._delete_file(lcov_out_file)
        self._delete_file(coverage_dir, dir_file=True)

        # Delete overall coverage files
        if all_files:
            self._delete_file(lcov_overall_file)
            self._delete_file(coverage_overall_dir, dir_file=True)

        # Remove Tar Files
        self._delete_file(f"{coverage_dir}.tar.gz")
        self._delete_file(f"{coverage_overall_dir}.tar.gz")

    def __del__(self):
        print(self.coverage_data.keys())
        print(self.coverage_data.values())
        if self.ssh_obj:
            # self.ssh_obj.close()
            pass


class POSTarget(Target):

    def __init__(self) -> None:
        super(POSTarget, self).__init__()
        self.pos_version = None
        self.pos_cli = "/bin/poseidonos-cli"
        pass

    def set_pos_path(self, path):
        return self.set_source_path(path)

    def get_pos_path(self):
        return self.get_source_path()

    def execute_cli(self, command):
        command = f"{self.get_pos_path()}/{self.pos_cli} {command}"
        return self.execute(command)


class Host():

    def __init__(self) -> None:
        pass

    def file_ops():
        pass


class Parser():

    def __init__(self) -> None:
        self.tar_path = None
        pass

    @classmethod
    def parse_indexfile(cls, coverage_file_path, csv_file_path) -> list:
        try:
            val_list = []
            f_open = open(csv_file_path, "w", newline="")
            f_out = csv.writer(f_open)
            headers = [
                "Type",
                "Coverage-Percentage",
            ]
            f_out.writerow(headers)
            for file in os.listdir(coverage_file_path):
                # logger.info(file)
                if "index.html" in file:
                    html_file_path = os.path.join(coverage_file_path, file)
                    with open(html_file_path) as index_file:
                        d = {}
                        soup = BeautifulSoup(index_file, "html.parser")
                        f_name_list = ["lines", "Functions", "Branches"]

                        f_lines_count = soup.find_all(
                            "td", attrs={'class': ['headerCovTableEntry']})
                        f_percentage_count = soup.find_all(
                            "td", attrs={'class': ['headerCovTableEntryLo']})
                        # f_name_list = list(f_name)
                        new_list = []
                        for i in range(0, len(f_lines_count), 2):
                            new_list.append(
                                [f_lines_count[i].text, f_lines_count[i+1].text])

                        for n in range(len(f_name_list)):
                            d[f_name_list[n]] = new_list[n] + \
                                [f_percentage_count[n].text]

                    for val in zip(list(d.keys()), list(d.values())):
                        f_out.writerow(val)
                        val_list.append(val)
            f_open.close()
        except Exception as e:
            logger.error(
                f"Parsing of index.html failed with error message: {e}")
        return val_list

    @classmethod
    def unzip_tar(cls, tar_file_path):
        cmd = f"tar -xvf {tar_file_path} -C /tmp"
        tar_out = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True)
        (o, e) = tar_out.communicate()
        if e:
            logger.error(
                f"Failed to unzip file '{tar_file_path}' due to '{e}'")
            return False
        return True

    @classmethod
    def prepare_overall_coverage_csv(cls, tar_file_path,
                                     coverage_file_path,
                                     csv_file_path) -> bool:
        if not cls.unzip_tar(tar_file_path):
            return False
        coverage_loc_path = f"/tmp/{coverage_file_path}/overall_coverage"
        try:
            overall_list = cls.parse_indexfile(
                coverage_loc_path, csv_file_path)
            logger.info(f"{overall_list}")
        except Exception as e:
            logger.info(f"Failed to prepare overall coverage csv. {e}")
            return False

        return True

    @classmethod
    def prepare_test_coverage_csv(cls, test_id, tar_file_path,
                                  coverage_file_path, csv_file_path) -> bool:
        if not cls.unzip_tar(tar_file_path):
            return False

        coverage_loc_path = "{}{}".format("/tmp", coverage_file_path)
        headers = ["file_path", "file_name", "func_name",
                   "Hit_count", "coverage", "TC_ID"]
        val_list = []
        try:
            with open(csv_file_path, "w", newline="") as csv_fp:
                csv_writer = csv.writer(csv_fp)
                csv_writer.writerow(headers)
                for root, dirs, files in os.walk(coverage_loc_path):
                    for file in files:
                        if file.endswith(".func.html"):
                            f_path = os.path.join(root, file)
                            with open(f_path) as html_fp:
                                d = {}
                                soup = BeautifulSoup(html_fp, "html.parser")
                                f_name = soup.find_all(
                                    "td", attrs={"class": ["coverFn"]}
                                )
                                f_count = soup.find_all(
                                    "td", attrs={"class": ["coverFnLo", "coverFnHi"]}
                                )
                                f_name_list = list(f_name)
                                f_count_list = list(f_count)
                                for l in range(len(f_name_list)):
                                    d[f_name_list[l].text] = f_count_list[l].text
                            rm_1 = f_path.replace(coverage_loc_path, "")
                            rm_2 = rm_1.replace(file, "")
                            if rm_2.startswith("/") and rm_2.endswith("/"):
                                rm_2 = rm_2[1:-1]
                            files_list = [rm_2] * len(list(d.keys()))
                            file_names = [file.replace(".func.html", "")] * len(
                                list(d.keys())
                            )
                            status = []
                            for key in d:
                                if int(d[key]) > 0:
                                    status.append("covered")
                                else:
                                    status.append("uncovered")
                            for val in zip(files_list, file_names, list(d.keys()),
                                           list(d.values()), status, test_id):
                                csv_writer.writerow(val)
                                val_list.append(val)
        except Exception as e:
            logger.error(f"Exception occured {e}")
            logger.error(f"Failed to prepare test {test_id} coverage csv")
            return False

        return True


class DBOperations():
        def __init__(self, connection=None) -> None:
            self.conn = connection
            self.test_coverage_table = None
            self.overall_coverage_table = None

        def connect(self, host_ip, user, passwd, database) -> bool:
            try:
                conn = mysql.connect(
                    host=host_ip, user=user, passwd=passwd, database=database,
                )
            except Exception as e:
                logger.error(f"Failed to connect to DB due to {e}")

            self.conn = conn
            logger.info("Connection to database is successful")
            
            return True

        def execute_query(self, query) -> bool:
            try:
                if not self.con.is_connected():
                    logger.error("DB connection does not exist")
                    return False
                conn = self.conn
                cur = conn.cursor()
                cur.execute(query)
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to execute the query {query} due to {e}")
                return False
            
            return True

        def create_coverage_main_table(self, table_name_suf='test') -> bool:
            if not self.con.is_connected():
                logger.error("DB connection does not exist")
                return False
                
            table_name = f"codecoverage{table_name_suf}"
            cur = self.con.cursor()
            cur.execute("select database();")
            record = cur.fetchone()
            logger.info("Connected to database: ", record)

            cur.execute(f"SHOW TABLES LIKE '{table_name}';")
            result = cur.fetchone()
            if table_name in result:
                logger.warning(f"The table {table_name} already exist")
                return True
            
            logger.info(f"Creating table {table_name}....")
            query = f"CREATE TABLE {table_name} (Type VARCHAR(25), Coverage_Percentage NUMERIC(5,2), "\
                     "FilePath VARCHAR(100), FileName VARCHAR(100),FuncName VARCHAR(1000), HitCount BIGINT, "\
                     "Coverage VARCHAR(25), Inc_Coverage VARCHAR(25), TCId VARCHAR(25), Version VARCHAR(25))"
                    
            cur.execute(query)
            self.test_coverage_table = table_name
            logger.info("The table {self.test_coverage_table} is created...")
            return True

        def create_coverage_overall_table(self, table_name_suf=None):
            if not self.con.is_connected():
                logger.error("DB connection does not exist")
                return False

            table_name = f"overallcodecoverage{table_name_suf}"
            cur = self.con.cursor()
            cur.execute(f"SHOW TABLES LIKE '{table_name}';")
            result = cur.fetchone()
            if table_name in result:
                logger.warning(f"The table {table_name} already exist")
                return True

            logger.info(f"Creating table {table_name}....")
            query = f"CREATE TABLE {table_name} (Type VARCHAR(25), Hit INT, "\
                    f"Total INT, overage_Percentage NUMERIC(5,2))"
            cur.execute(query)

            self.overall_coverage_table = table_name
            logger.info("The table {self.overall_coverage_table} is created...")
            return True

        def insert_code_coverage_data(self, val_list, version=None,
                                      Inc_Coverage=None) -> bool:
            for val in val_list:
                query = f"insert into codecoveragetest(FilePath,FileName,FuncName,HitCount,Coverage,TCId,Version,Inc_Coverage) "\
                        f"values('{val[0]}','{val[1]}','{val[2]}',{val[3]},'{val[4]}','{val[5]}','{version}','{Inc_Coverage}')"

                if not self.execute_query(self, query):
                    logger.error("Failed to Insert data to databse")
                    return False
                else:
                    logger.info("Successfully Inserted data to database")
                
            return True

        def insert_overall_data(self, val_list, table_name, version=None, 
                        tc_name=None, Inc_Coverage=None) -> bool:
            for val in val_list:
                val_pcent = val[1][2].split("%")[0]
                if table_name == self.overall_coverage_table:
                    query = f"insert into {table_name}(Type,Hit,Total,Coverage_Percentage) "\
                            f"values('{val[0]}','{val[1][0]}','{val[1][1]}','{val_pcent}')"
                elif table_name == self.test_coverage_table:
                    query = f"insert into {table_name}(Type,Coverage_Percentage,TCID,Version,Inc_Coverage) "\
                            f"values('{val[0]}','{val_pcent}','{tc_name}','{version}','{Inc_Coverage}')"

                if not self.execute(query):
                    logger.error(f"Failed to insert data in table {table_name}")
                    return False

                logger.ingo(f"Data inserted in the table {table_name}")
                return True
                    
        def update_overall_data(self, val_list):
            try:
                table_name = self.overall_coverage_table
                for val in val_list:
                    cov_pcent = val[1][2].split("%")[0]
                    hit = val[1][0]
                    total = val[1][1]
                    type = val[0]
                    query = "update {} set Hit={},Total={},Coverage_Percentage={} where "\
                            "Type='{}'".format(table_name, hit, total, cov_pcent, type)
                    cur = self.con.cursor()
                    cur.execute(query)
                    self.con.commit()
            except Exception as e:
                logger.error(f"Data is not updated in {table_name} table due to {e}")

class CodeCoverage():

    def __init__(self) -> None:
        self.target = POSTarget()
        self.parser = Parser()
        self.topology_data = None
        pass

    def __config_gcov(self):
        pass

    def load_topology(self, topology_file=None, abs_path=False):
        if not topology_file:
            topology_file = "topology.json"

        if not abs_path:
            file_dir = os.path.join(os.path.dirname(__file__),
                                    "../testcase/config_files")
            file_abs_path = os.path.abspath(file_dir)
            file_name = "{}/{}".format(file_abs_path, topology_file)
        else:
            file_name = topology_file

        if not os.path.exists(file_name):
            logger.error("File {} does not exist".format(file_name))
            return False
        try:
            with open(f"{file_name}") as f:
                self.topology_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read {file_name} due to {e}")
            return False

        return True

    def connect_target(self, target_obj=None):
        if target_obj:
            if not self.target.set_connection(target_obj):
                logger.error("Failed to connect to target")
                return False
        else:
            if not self.load_topology() or not self.topology_data:
                logger.error("Failed to load topology file")
                return False

            data_dict = self.topology_data
            tgt_ip_addr = data_dict["login"]["target"]["server"][0]["ip"]
            tgt_user_id = data_dict["login"]["target"]["server"][0]["username"]
            tgt_password = data_dict["login"]["target"]["server"][0]["password"]

            if not self.target.connect(tgt_ip_addr, tgt_user_id, tgt_password):
                logger.error("Failed to connect to target.")
                return False

            tgt_pos_path = data_dict["login"]["paths"]["pos_path"]

        if not self.target.set_pos_path(tgt_pos_path):
            logger.error("Failed to set pos path")
            return False

        if not self.target.set_lcov_path("/usr/bin/lcov"):
            logger.error("Failed to set lcov path")
            return False

        return True

    def get_code_coverage(self, jira_id):
        if not self.target.verify_coverage_pre():
            logger.error("Target code coverage precondition is not done")
            return False

        if not self.target.generate_coverage(jira_id):
            logger.error("Failed to get code coverage")
            return False

        if not self.target.generate_html_report(jira_id):
            logger.error("Failed to generate html report")
            return False

        if not self.target.fetch_coverage_report(jira_id):
            logger.error("Failed to fetch the coverage report")
            return False

        self.target.delete_coverage_files(jira_id)
        return True

    def parse_coverage_report(self, jira_id):
        jira_id = jira_id.upper()
        test_file_dict = self.target.get_coverage_data_dict(jira_id)
        if not test_file_dict or not test_file_dict["file_transfered"]:
            logger.error("Failed to get the coverage file information")
            return False

        unique_key = test_file_dict["unique_key"]
        tar_file_path = f"/tmp/coverage_{jira_id}_{unique_key}.tar"
        csv_file_path = f"/tmp/coverage_{jira_id}_{unique_key}.csv"
        coverage_file_path = "/root/pos-0.11.0-rc5/ibofos/"
        if not self.parser.prepare_test_coverage_csv(jira_id, tar_file_path,
                                                     coverage_file_path, csv_file_path):
            logger.error("Failed to prepare test coverage csv")

        tar_file_path = f"/tmp/overall_coverage.tar"
        csv_file_path = f"/tmp/overall_coverage.csv"

        if not self.parser.prepare_overall_coverlsage_csv(jira_id, tar_file_path,
                                                        coverage_file_path, csv_file_path):
            logger.error("Failed to prepare overall coverage csv")

        return True

    def save_coverage_report(self, jira_id):
        pass


if __name__ == '__main__':
    jira_id = "SPS_1100"
    #cc = CodeCoverage()
    #assert cc.connect_target()
    #assert cc.get_code_coverage(jira_id)
    #assert cc.parse_coverage_report(jira_id)

    coverage_file_path = "/root/pos-0.11.0-rc5/ibofos/"
    tar_file_path = f"/tmp/overall_coverage.tar"
    csv_file_path = f"/tmp/overall_coverage.csv"
    parser = Parser()
    if not parser.prepare_overall_coverage_csv(tar_file_path,
                                               coverage_file_path, csv_file_path):
        logger.error("Failed to prepare overall coverage csv")

    pass
