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

from .exceptions import InvalidPlatformError
from distutils import dir_util
import scar.logger as logger
import base64
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

def resource_path(relative_path, bin_path=None):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        if bin_path:
            return bin_path
        else:
            base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def is_binary_execution():
    try:
        binary_env = sys._MEIPASS
        if platform.system().lower() != 'linux':
            raise InvalidPlatformError()
        return True
    except Exception:
        return False

def copy_file(source, dest):
    shutil.copy(source, dest)

def copy_dir(source, dest):    
    dir_util.copy_tree(source, dest)    
    
def get_scar_root_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def join_paths(*paths):
    return os.path.join(*paths)

def get_tmp_dir():
    return tempfile.gettempdir()

def create_tmp_dir():
    return tempfile.TemporaryDirectory()

def lazy_property(func):
    ''' A decorator that makes a property lazy-evaluated.'''
    attr_name = '_lazy_' + func.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    return _lazy_property

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

def divide_list_in_chunks(elements, chunk_size):
    """Yield successive n-sized chunks from th elements list."""
    if len(elements) == 0:
        yield []
    for i in range(0, len(elements), chunk_size):
        yield elements[i:i + chunk_size]
        
def get_random_uuid4_str():
    return str(uuid.uuid4())

def merge_dicts(d1, d2):
    '''
    Merge 'd1' and 'd2' dicts into 'd1'.
    'd2' has precedence over 'd1'
    '''
    for k,v in d2.items():
        if v:
            if k not in d1:
                d1[k] = v
            elif type(v) is dict:
                d1[k] = merge_dicts(d1[k], v)
            elif type(v) is list:
                d1[k] += v
    return d1

def is_value_in_dict(value, dictionary):
    return value in dictionary and dictionary[value]

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
    if os.path.isfile(path):
        os.remove(path)

def delete_folder(path):
    shutil.rmtree(path)
    
def create_tar_gz(files_to_archive, destination_tar_path):
    with tarfile.open(destination_tar_path, "w:gz") as tar:
        for file_path in files_to_archive:
            tar.add(file_path, arcname=os.path.basename(file_path))
    return destination_tar_path
      
def extract_tar_gz(tar_path, destination_path):
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=destination_path)

def kill_process(self, process):
    # Using SIGKILL instead of SIGTERM to ensure the process finalization 
    os.killpg(os.getpgid(process.pid), subprocess.signal.SIGKILL)

def execute_command(command):
    subprocess.call(command)
    
def execute_command_and_return_output(command):
    return subprocess.check_output(command).decode("utf-8")

def is_variable_in_environment(variable):
    return is_value_in_dict(variable, os.environ)

def set_environment_variable(key, variable):
    if key and variable:
        os.environ[key] = variable

def get_environment_variable(variable):
    if is_variable_in_environment(variable):
        return os.environ[variable]
    
def delete_environment_variable(variable):
    if is_variable_in_environment(variable):
        del os.environ[variable]

def parse_arg_list(arg_keys, cmd_args):
    result = {}
    for key in arg_keys:
        if type(key) is tuple:
            if key[0] in cmd_args and cmd_args[key[0]]:
                result[key[1]] = cmd_args[key[0]]
        else:
            if key in cmd_args and cmd_args[key]:
                result[key] = cmd_args[key]
    return result

def get_user_defined_variables():
    user_vars = {}
    for key in os.environ.keys():
        # Find global variables with the specified prefix
        if re.match("CONT_VAR_.*", key):
            user_vars[key.replace("CONT_VAR_", "")] = get_environment_variable(key)
    return user_vars

def unzip_folder(zip_path, folder_where_unzip_path):
    '''Must use the unzip binary to preserve the file properties and the symlinks'''
    zip_exe = resource_path("src/bin/unzip", bin_path='/usr/bin/unzip')
    execute_command_with_msg([zip_exe, zip_path], cmd_wd=folder_where_unzip_path, cli_msg="Creating function package")    
                
def zip_folder(zip_path, folder_to_zip_path, msg=""):
    '''Must use the zip binary to preserve the file properties and the symlinks'''
    zip_exe = resource_path("src/bin/zip", bin_path='/usr/bin/zip')
    execute_command_with_msg([zip_exe, "-r9y", zip_path, "."],
                             cmd_wd=folder_to_zip_path,
                             cli_msg=msg)
    
def execute_command_with_msg(command, cmd_wd=None, cli_msg=None):
    cmd_out = subprocess.check_output(command, cwd=cmd_wd).decode("utf-8")
    logger.debug(cmd_out)
    logger.info(cli_msg)
    return cmd_out[:-1]

def get_storage_provider_id(storage_provider, env_vars):
    '''
    Searches the storage provider id in the environment variables:
        get_provider_id(S3, {'STORAGE_AUTH_S3_41807_USER' : 'scar'})
        returns -> 41807
    '''
    for env_key in env_vars.keys():
        if env_key.startswith("STORAGE_AUTH_{}".format(storage_provider)):
            return "_".join(env_key.split("_")[3:-1])

