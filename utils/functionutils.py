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
import logging
import os
import re
import sys
import zipfile

def is_valid_name(function_name):
    if function_name:
        aws_name_regex = "(arn:(aws[a-zA-Z-]*)?:lambda:)?([a-z]{2}(-gov)?-[a-z]+-\d{1}:)?(\d{12}:)?(function:)?([a-zA-Z0-9-_]+)(:(\$LATEST|[a-zA-Z0-9-_]+))?"           
        pattern = re.compile(aws_name_regex)
        func_name = pattern.match(function_name)
        return func_name and (func_name.group() == function_name)
    return False    

def finish_failed_execution():
    logging.info('SCAR execution finished with errors')
    logging.info('----------------------------------------------------')
    sys.exit(1)

def finish_successful_execution():
    logging.info('SCAR execution finished')
    logging.info('----------------------------------------------------')
    sys.exit(0)

def find_expression(rgx_pattern, string_to_search):
    '''Returns the first group that matches the rgx_pattern in the string_to_search'''
    pattern = re.compile(rgx_pattern)
    match = pattern.search(string_to_search)
    if match :
        return match.group()

def base64_to_utf8(value):
    return base64.b64decode(value).decode('utf8')

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

def parse_payload(value):
    value['Payload'] = value['Payload'].read().decode("utf-8")[1:-1].replace('\\n', '\n')
    return value

def parse_base64_response_values(value):
    value['LogResult'] = base64_to_utf8(value['LogResult'])
    value['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'] = base64_to_utf8(value['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'])
    return value

def parse_log_ids(value):
    parsed_output = value['Payload'].split('\n')
    value['LogGroupName'] = parsed_output[1][22:]
    value['LogStreamName'] = parsed_output[2][23:]
    return value

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

def add_file_to_zip(zip_path, file_path, file_name):
    with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zf:
        zf.write(file_path, 'extra/' + file_name)

def zip_folder(zip_path, target_dir):            
    with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zf:
        rootlen = len(target_dir) + 1
        for base, _, files in os.walk(target_dir):
            for file in files:
                fn = os.path.join(base, file)
                zf.write(fn, 'extra/' + fn[rootlen:])
                
def get_file_as_byte_array(file_path):
    # Return the zip as an array of bytes
    with open(file_path, 'rb') as f:
        return f.read()
