import os
import glob
import re
logcwd = f'{os.getcwd()}/logs/*'
print(logcwd)
list_of_files = glob.glob(logcwd)
latest_file = max(list_of_files, key=os.path.getctime)
htm = f'{latest_file}/report.html'

with open(htm,"r") as report:
     output=report.readlines()
     for line in output:
         print(line)
         if '<span class="passed">' in line:
            passed=re.findall('<span class="passed">(\d+)',line)
            failed=re.findall('<span class="failed">(\d+)',line)
with open("pos.txt","a+") as textreport:
     textreport.write("Pass = {}\nFail= {}\n".format(passed[0],failed[0]))
