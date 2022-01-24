# Trident
Trident is a framework to test and explore Poseidon OS (POS). It has python APIs for all the POS CLI commands, for user to develop their own test suite.
It is built on top of pytest framework, The tool contains following test cases to cover base scenarios:
- Array, Volume management (create, delete, rename)
- User IO (Block, File IO, various IO types e.g. sync/async)
- Array rebuild (SSD hot plug)
- GC and flush

A setup tool is developed to check if setup is ready for test execution.

# Table of contents
- [Download the Source Code](#download-the-source-code)
- [Install Prerequisites](#install-prerequisites)
- [Download and Build POS](#download-and-build-pos)
- [Updating Trident config](#updating-trident-config)
- [Run Test cases](#run-test-cases)
- [Notes](#notes)
# Download the Source Code

`$git clone https://github.com/poseidonos/trident.git`

# Install Prerequisites
`$pip3 install --upgrade pip`

`$pip3 install -r requirements.txt`

# Download and Build POS
Please refer to https://github.com/poseidonos/poseidonos/blob/main/README.md 

# Updating Trident config
Update testcases/config_files/topology.json with system details such as IP addresses and POS path

Test the system by executing setup tool from utils

`$python3 utils/setup_tool.py all`

Please refer docs/UserGuide.md for details

# Run Test cases
`$python3 -m pytest -v  testcase/array/test_array.py::test_create_check`

Please refer docs/UserGuide.md for details

# Notes
Trident currently supports 0.10.x version of Poseidon OS

