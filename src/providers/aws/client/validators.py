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

def validate_function_properties(_lambda):
    validate_iam_role(_lambda.get_property("iam"))
    validate_function_name(_lambda.get_property("name"),
                           _lambda.get_property("name_regex"))
    validate_time(_lambda.get_property("time"))
    validate_memory(_lambda.get_property("memory"))

def validate_iam_role(iam_props):
    if (("role" not in iam_props) or (iam_props["role"] == "")):
        raise Exception("Please, specify a valid iam role in the configuration file (usually located in ~/.scar/scar.cfg).")

def validate_time(lambda_time):
    if (lambda_time <= 0) or (lambda_time > 300):
        raise Exception('Incorrect time specified\nPlease, set a value between 0 and 300.')
    return lambda_time

def validate_memory(lambda_memory):
    """ Check if the memory introduced by the user is correct.
    If the memory is not specified in 64mb increments,
    transforms the request to the next available increment."""
    if (lambda_memory < 128) or (lambda_memory > 1536):
        raise Exception('Incorrect memory size specified\nPlease, set a value between 128 and 1536.')
    else:
        res = lambda_memory % 64
        if (res == 0):
            return lambda_memory
        else:
            return lambda_memory - res + 64
        
def validate_function_name(function_name, name_regex):
    if not utils.is_valid_string(function_name, name_regex):
        raise Exception("'%s' is an invalid lambda function name." % function_name)
        #logger.error("'%s' is an invalid lambda function name." % function_name)
        #utils.finish_failed_execution()  
        