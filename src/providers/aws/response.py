# SCAR - Serverless Container-aware ARchitectures
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

from enum import Enum
from tabulate import tabulate
import src.logger as logger
import src.utils as utils

class OutputType(Enum):
    PLAIN_TEXT = 1
    JSON = 2
    VERBOSE = 3

def print_generic_response(response, output_type, aws_output, text_message=None, json_output=None, verbose_output=None):
    if output_type == OutputType.PLAIN_TEXT:
        output = text_message
        logger.info(output, output)
    else:
        if output_type == OutputType.JSON:
            if json_output:
                output = json_output
            else:
                output = { aws_output : {'RequestId' : response['ResponseMetadata']['RequestId'],
                                          'HTTPStatusCode' : response['ResponseMetadata']['HTTPStatusCode']}}         
        elif output_type == OutputType.VERBOSE:
            if verbose_output:
                output = verbose_output
            else:
                output = { aws_output : response }        
        logger.info_json(output, output)

def parse_lambda_function_creation_response(response, function_name, access_key, output_type):
    aws_output = 'LambdaOutput'
    text_message = "Function '%s' successfully created." % function_name
    json_message = { aws_output : {'AccessKey' : access_key,
                                    'FunctionArn' : response['FunctionArn'],
                                    'Timeout' : response['Timeout'],
                                    'MemorySize' : response['MemorySize'],
                                    'FunctionName' : response['FunctionName']}}
    print_generic_response(response, output_type, aws_output, text_message, json_output=json_message)

def parse_log_group_creation_response(response, log_group_name, output_type):
    text_message = "Log group '%s' successfully created." % log_group_name
    print_generic_response(response, output_type, 'CloudWatchOutput', text_message)

def parse_delete_function_response(response, function_name, output_type):
    text_message = "Function '%s' successfully deleted." % function_name
    print_generic_response(response, output_type, 'LambdaOutput', text_message)

def parse_delete_log_response(response, log_group_name, output_type):
    text_message = "Log group '%s' successfully deleted." % log_group_name
    print_generic_response(response, output_type, 'CloudWatchOutput', text_message)  

def parse_ls_response(lambda_functions, output_type):
    aws_output = 'Functions'
    result = []
    text_message = ""
    if output_type == OutputType.VERBOSE:
        result = lambda_functions
    else:
        for _lambda in lambda_functions:
            result.append(parse_lambda_function_info(_lambda))
        text_message = get_table(result)    
    json_message = { aws_output : result }
    print_generic_response('', output_type, aws_output, text_message, json_output=json_message, verbose_output=json_message)    
    

def parse_lambda_function_info(function_info):
    name = function_info.get('FunctionName', "-")
    memory = function_info.get('MemorySize', "-")
    timeout = function_info.get('Timeout', "-")
    image_id = function_info['Environment']['Variables'].get('IMAGE_ID', "-")
    return {'Name' : name,
            'Memory' : memory,
            'Timeout' : timeout,
            'Image_id': image_id}
  
def get_table(functions_info):
    headers = ['NAME', 'MEMORY', 'TIME', 'IMAGE_ID']
    table = []
    for function in functions_info:
        table.append([function['Name'],
                      function['Memory'],
                      function['Timeout'],
                      function['Image_id']])
    return tabulate(table, headers)    

def parse_error_invocation_response(response, function_name):
    if "Task timed out" in response['Payload']:
        # Find the timeout time
        message = utils.find_expression('(Task timed out .* seconds)', str(response['Payload']))
        # Modify the error message to ease the error readability
        error_msg = message.replace("Task", "Function '%s'" % function_name)
        error_log = "Error in function response: %s" % error_msg                
    else:
        error_msg = "Error in function response."
        error_log = "Error in function response: %s" % response['Payload']
    logger.error(error_msg, error_log)
    utils.finish_failed_execution()    
        
def parse_payload(value):
    if (('Payload' in value) and value['Payload']):
        value['Payload'] = value['Payload'].read().decode("utf-8")[1:-1].replace('\\n', '\n')
        return value
    else:
        return ''
    
def parse_asynchronous_invocation_response(response, output_type, function_name):
    aws_output = 'LambdaOutput'
    text_message = "Function '%s' launched correctly" % function_name
    json_message = { aws_output : {'StatusCode' : response['StatusCode'],
                                   'RequestId' : response['ResponseMetadata']['RequestId']}}        
    print_generic_response(response, output_type, aws_output, text_message, json_output=json_message)
    
def parse_requestresponse_invocation_response(response, output_type):
    aws_output = 'LambdaOutput'
    text_message = 'SCAR: Request Id: %s\n' % response['ResponseMetadata']['RequestId']
    text_message += response['Payload']
    json_message = { aws_output : {'StatusCode' : response['StatusCode'],
                                   'Payload' : response['Payload'],
                                   'LogGroupName' : response['LogGroupName'],
                                   'LogStreamName' : response['LogStreamName'],
                                   'RequestId' : response['ResponseMetadata']['RequestId']}}        
    print_generic_response(response, output_type, aws_output, text_message, json_output=json_message)        
      
def parse_base64_response_values(value):
    value['LogResult'] = utils.base64_to_utf8(value['LogResult'])
    value['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'] = utils.base64_to_utf8(value['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'])
    return value

def parse_log_ids(value):
    parsed_output = value['Payload'].split('\n')
    value['LogGroupName'] = parsed_output[1][22:]
    value['LogStreamName'] = parsed_output[2][23:]
    return value
        
def parse_invocation_response(response, function_name, output_type, is_asynchronous):
    # Decode and parse the payload
    response = parse_payload(response)
    if "FunctionError" in response:
        parse_error_invocation_response(response, function_name)
    if is_asynchronous:        
        parse_asynchronous_invocation_response(response, output_type, function_name)
    else:
        # Transform the base64 encoded results to something legible
        response = parse_base64_response_values(response)
        # Extract log_group_name and log_stream_name from the payload
        response = parse_log_ids(response)
        parse_requestresponse_invocation_response(response, output_type)
        
