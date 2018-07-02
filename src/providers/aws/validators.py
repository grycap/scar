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

import src.utils as utils
from botocore.exceptions import ClientError

def create_clienterror(error_msg, operation_name):
    error = {'Error' : {'Message' : error_msg}}
    return ClientError(error, operation_name)

def validate_iam_role(iam_props):
    if (("role" not in iam_props) or (iam_props["role"] == "")):
        error_msg = "Please, specify a valid iam role in the configuration file (usually located in ~/.scar/scar.cfg)."
        raise create_clienterror(error_msg, 'validate_iam_role')

def validate_time(lambda_time):
    if (lambda_time <= 0) or (lambda_time > 300):
        error_msg = 'Incorrect time specified\nPlease, set a value between 0 and 300.'
        raise create_clienterror(error_msg, 'validate_time')

def validate_memory(lambda_memory):
    if (lambda_memory < 128) or (lambda_memory > 3008):
        error_msg = 'Incorrect memory size specified\nPlease, set a value between 128 and 3008.'
        raise create_clienterror(error_msg, 'validate_memory')
        
def validate_function_name(function_name, name_regex):
    if not utils.find_expression(function_name, name_regex):
        raise Exception("'{0}' is an invalid lambda function name.".format(function_name))

def validate(**kwargs):
    if 'MemorySize' in kwargs:
        validate_memory(kwargs['MemorySize'])
    if 'Timeout' in kwargs:
        validate_time(kwargs['Timeout'])        
    
            