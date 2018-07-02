# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) 2011 - GRyCAP - Universitat Politecnica de Valencia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
import json
import os
import re
import sys
import uuid
import functools
import subprocess
import tarfile
from botocore.exceptions import ClientError
from . import logger

def lazy_property(func):
    ''' A decorator that makes a property lazy-evaluated.'''
    attr_name = '_lazy_' + func.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    return _lazy_property

def exception(logger):
    '''
    A decorator that wraps the passed in function and logs exceptions
    @param logger: The logging object
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ClientError as ce:
                print("There was an exception in {0}".format(func.__name__))
                print(ce.response['Error']['Message'])
                logger.exception(ce)
            except Exception as ex:
                print("There was an exception in {0}".format(func.__name__))
                logger.exception(ex)
                # re-raise the exception
                # raise
        return wrapper
    return decorator

def finish_failed_execution(error_msg=None, ex=None):
    if error_msg and ex:
        logger.error(error_msg, error_msg + ": {0}".format(ex)) 
    logger.end_execution_trace_with_errors()
    sys.exit(1)

def finish_successful_execution():
    logger.end_execution_trace()
    sys.exit(0)

def find_expression(string_to_search, rgx_pattern):
    '''Returns the first group that matches the rgx_pattern in the string_to_search'''
    if string_to_search:    
        pattern = re.compile(rgx_pattern)
        match = pattern.search(string_to_search)
        if match :
            return match.group()

def base64_to_utf8_string(value):
    return base64.b64decode(value).decode('utf-8')

def utf8_to_base64_string(value):
    return base64.b64encode(value).decode('utf-8')

def dict_to_base64_string(value):
    return base64.b64encode(json.dumps(value)).decode("utf-8")

def print_json(value):
    print(json.dumps(value))
    
def divide_list_in_chunks(elements, chunk_size):
    """Yield successive n-sized chunks from th elements list."""
    if len(elements) == 0:
        yield []
    for i in range(0, len(elements), chunk_size):
        yield elements[i:i + chunk_size]
        
def get_random_uuid4_str():
    return str(uuid.uuid4())

def has_dict_prop_value(dictionary, value):
    return (value in dictionary) and dictionary[value] and (dictionary[value] != "")

def load_json_file(file_path):
    if os.path.isfile(file_path):
        with open(file_path) as f:
            return json.load(f)
        
def merge_dicts(d1, d2):
    for k,v in d2.items():
        if v:
            d1[k] = v
    return d1

def check_key_in_dictionary(key, dictionary):
    return (key in dictionary) and dictionary[key] and dictionary[key] != ""

def get_tree_size(path):
    """Return total size of files in given path and subdirs."""
    total = 0
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            total += get_tree_size(entry.path)
        else:
            total += entry.stat(follow_symlinks=False).st_size
    return total

def get_all_files_in_directory(dir_path):
    files = []
    for dirname, _, filenames in os.walk(dir_path):
        for filename in filenames:
            files.append(os.path.join(dirname, filename))
    return files

def get_file_size(file_path):
    '''Return file size in bytes'''
    return os.stat(file_path).st_size

def create_folder(folder_name):
    if not os.path.isdir(folder_name):
        os.makedirs(folder_name, exist_ok=True)
        
def create_file_with_content(path, content):
    with open(path, "w") as f:
        f.write(content)

def read_file(file_path, mode="r"):
    with open(file_path, mode) as content_file:
        return content_file.read()
    
def delete_file(path):
    os.remove(path)
    
def create_tar_gz(files_to_archive, destination_tar_path):
    with tarfile.open(destination_tar_path, "w:gz") as tar:
        for file_path in files_to_archive:
            tar.add(file_path, arcname=os.path.basename(file_path))
    return destination_tar_path
        
def extract_tar_gz(tar_path, destination_path):
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=destination_path)
    logger.info("Successfully extracted '%s' in path '%s'" % (tar_path, destination_path))    

def kill_process(self, process):
    logger.info("Stopping process '{0}'".format(process))
    # Using SIGKILL instead of SIGTERM to ensure the process finalization 
    os.killpg(os.getpgid(process.pid), subprocess.signal.SIGKILL)

def execute_command(command):
    subprocess.call(command)
    
def execute_command_and_return_output(command):
    return subprocess.check_output(command).decode("utf-8")

def is_variable_in_environment(variable):
    return check_key_in_dictionary(variable, os.environ)

def set_environment_variable(key, variable):
    if key and variable and key != "" and variable != "":
        os.environ[key] = variable

def get_environment_variable(variable):
    if check_key_in_dictionary(variable, os.environ):
        return os.environ[variable]

