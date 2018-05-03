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
import src.logger as logger
import os
import re
import sys
import uuid

def lazy_property(fn):
    '''Decorator that makes a property lazy-evaluated.'''
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property

def is_valid_string(value, regex):
    ''' Check if the passed value is valid using the passed regex'''
    if value:
        pattern = re.compile(regex)
        func_name = pattern.match(value)
        return func_name and (func_name.group() == value)
    return False    

def finish_failed_execution():
    logger.end_execution_trace_with_errors()
    sys.exit(1)

def finish_successful_execution():
    logger.end_execution_trace()
    sys.exit(0)

def find_expression(rgx_pattern, string_to_search):
    '''Returns the first group that matches the rgx_pattern in the string_to_search'''
    pattern = re.compile(rgx_pattern)
    match = pattern.search(string_to_search)
    if match :
        return match.group()

def base64_to_utf8(value):
    return base64.b64decode(value).decode('utf8')

def dict_to_base64_string(value):
    return base64.b64encode(json.dumps(value)).decode("utf-8")

def escape_list(values):
    result = []
    for value in values:
        result.append(escape_string(value))
    return str(result).replace("'", "\"")

def escape_string(value):
    value = value.replace("\\", "\\/").replace('\n', '\\n')
    value = value.replace('"', '\\"').replace("\/", "\\/")
    value = value.replace("\b", "\\b").replace("\f", "\\f")
    return value.replace("\r", "\\r").replace("\t", "\\t")

def print_json(value):
    print(json.dumps(value))
    
def divide_list_in_chunks(elements, chunk_size):
    """Yield successive n-sized chunks from th elements list."""
    if len(elements) == 0:
        yield []
    for i in range(0, len(elements), chunk_size):
        yield elements[i:i + chunk_size]
        
def delete_file(path):
    os.remove(path)

def get_file_as_byte_array(file_path):
    # Return the zip as an array of bytes
    with open(file_path, 'rb') as f:
        return f.read()
    
def get_random_uuid4_str():
    return str(uuid.uuid4())

def has_dict_prop_value(dictionary, value):
    if (value in dictionary) and (dictionary[value] != ""):
        return True
    else:
        return False

def load_json_file(file_path):
    if os.path.isfile(file_path):
        with open(file_path) as f:
            return json.load(f)
        
def merge_dicts(d1, d2):
    for k,v in d2.items():
        if v is not None:
            
            d1[k] = v
    return d1

def get_tree_size(path):
    """Return total size of files in given path and subdirs."""
    total = 0
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            total += get_tree_size(entry.path)
        else:
            total += entry.stat(follow_symlinks=False).st_size
    return total     
