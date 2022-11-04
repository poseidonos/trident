import os
import glob
import re

logcwd = f"{os.getcwd()}/logs/*"
print(logcwd)
list_of_files = glob.glob(logcwd)
latest_file = max(list_of_files, key=os.path.getctime)
htm = f"{latest_file}/report.html"
def make_dir(path = "results"):
    if not os.path.exists(path):
        os.makedirs(path)
with open(htm, "r") as report:
    output = report.readlines()
    for line in output:
        
        if '<span class="passed">' in line:
            passed = re.findall('<span class="passed">(\d+)', line)
            failed = re.findall('<span class="failed">(\d+)', line)
report.close()
with open("results/pos_poc3_Summary.txt", "a+") as textreport:
    textreport.write("Pass = {}\nFail= {}\n".format(passed[0], failed[0]))

with open("results/pos_report.html", "a+") as report:
    for line in output:
        report.write(line)
report.close()
