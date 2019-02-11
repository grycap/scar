# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os

log_folder_name = ".scar"
log_file_folder = os.path.join(os.path.expanduser("~"), log_folder_name)
if 'SCAR_LOG_PATH' in os.environ:
    log_file_folder = os.environ['SCAR_LOG_PATH']
log_file_name = "scar.log"
log_file_path = os.path.join(log_file_folder, log_file_name)

# Create scar config dir
if not os.path.isdir(log_file_folder):
    os.makedirs(log_file_folder, exist_ok=True)

loglevel = logging.INFO
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename=log_file_path, level=loglevel, format=FORMAT)

def init_execution_trace():
    logging.info('----------------------------------------------------')
    logging.info('SCAR execution started')
    
def end_execution_trace():
    logging.info('SCAR execution finished')
    logging.info('----------------------------------------------------')     
        
def end_execution_trace_with_errors():
    logging.info('SCAR execution finished with errors')
    logging.info('----------------------------------------------------')

def debug(cli_msg, log_msg=None):
    if loglevel == logging.DEBUG:
        print(cli_msg)
    logging.debug(log_msg) if log_msg else logging.debug(cli_msg)

def info(cli_msg=None, log_msg=None):
    if cli_msg and loglevel == logging.INFO:
        print(cli_msg)
    logging.info(log_msg) if log_msg else logging.info(cli_msg)

def warning(cli_msg, log_msg=None):
    print(cli_msg)
    logging.warning(log_msg) if log_msg else logging.warning(cli_msg)

def error(cli_msg, log_msg=None):
    if log_msg:
        print(log_msg)
        logging.error(log_msg)
    else:
        print(cli_msg)
        logging.error(cli_msg)
        
def exception(msg):
    logging.exception(msg)        

def log_exception(error_msg, exception):
    error(error_msg, error_msg + ": {0}".format(exception))

def print_json(value):
    print(json.dumps(value))

def info_json(cli_msg, log_msg=None):
    print_json(cli_msg)
    logging.info(log_msg) if log_msg else logging.info(cli_msg)

def warning_json(cli_msg, log_msg=None):
    print_json(cli_msg)
    logging.warning(log_msg) if log_msg else logging.warning(cli_msg)

def error_json(cli_msg, log_msg=None):
    print_json(cli_msg)
    logging.error(log_msg) if log_msg else logging.error(cli_msg)          
