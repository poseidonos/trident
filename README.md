#Trident open source 

Intro:

Trident is an open source NVMe-oF pytest cli based test framework which is 
basically designed to test the basic Poseidon storage os features. It provides 
API's and fixtures which enables to write their own tests easily.

Features:
1. usage of Parametrization helps generate test combinations
2. Automatic generation of Html report after test execution 
3. Minimal usage of python internal modules 
4. Extensive usage of conftest.py at test case level which helps with minimal 
   code in test case 
5. Supports all POS cli commands 
6. Tests can be run on a single machine i.e; machine with 4 nvme drives can be 
   used as Target, Initiator & Executor machine.
7. With minimal changes test framework transport can be switched in tcp or rdma 

Steps to Install pre-requisites:
1. Ensure python3 is installed
2. Install python3-pip package required to install python packages
3. upgrade pip to the latest version (command : pip3 install --upgrade pip)
4. Navigate to ibot directory and run requirements.txt file 
   (command : pip3 install -r requirements.txt)

Documentation:
1. Documentation for test framework is generated using doxygen tool
2. After clonning install doxygen and its dependencies 
3. Navigate to docs/doxygen folder and run doxygen command which generated html
   folder which will have required documentation for methods.
