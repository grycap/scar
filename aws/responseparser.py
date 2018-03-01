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

import logging
import utils.outputtype as outputType
from tabulate import tabulate
import json
import utils.functionutils as utils

def parse_generic_response(response, text_message, output_type, verbose_output=None, json_output=None):
    if output_type == outputType.PLAIN_TEXT:
        output = text_message
    else:
        if output_type == outputType.VERBOSE:
            if verbose_output:
                output = verbose_output
            else:
                output = {'CloudWatchOuput': response}
        elif output_type == outputType.JSON:
            if json_output:
                output = json_output
            else:
                output = {'CloudWatchOutput': {'RequestId' : response['ResponseMetadata']['RequestId'],
                                               'HTTPStatusCode' : response['ResponseMetadata']['HTTPStatusCode']}}
    print(utils.json_to_string(output))
    logging.info(output)

class ResponseParser(object):
 
    def parse_lambda_function_creation_response(self, lambda_response, function_name, access_key, output_type):
        text_message = "Function '%s' successfully created." % function_name
        json_message = {'LambdaOutput' : {'AccessKey' : access_key,
                                          'FunctionArn' : lambda_response['FunctionArn'],
                                          'Timeout' : lambda_response['Timeout'],
                                          'MemorySize' : lambda_response['MemorySize'],
                                          'FunctionName' : lambda_response['FunctionName']}}
        parse_generic_response(lambda_response, text_message, output_type, json_output=json_message)
    
    def parse_log_group_creation_response(self, cw_response, log_group_name, output_type):
        text_message = "Log group '%s' successfully created." % log_group_name
        parse_generic_response(cw_response, text_message, output_type)
    
    def parse_delete_function_response(self, lambda_response, function_name, output_type):
        text_message = "Function '%s' successfully deleted." % function_name
        parse_generic_response(lambda_response, text_message, output_type)

    def parse_delete_log_response(self, cw_response, log_group_name, output_type):
        text_message = "Log group '%s' successfully deleted." % log_group_name
        parse_generic_response(cw_response, text_message, output_type)    

    def parse_ls_response(self, lambda_function_info_list, output_type):
        # Create the data structure
        if output_type == outputType.VERBOSE:
            functions_full_info = []
            [functions_full_info.append(function_info) for function_info in lambda_function_info_list]
            print('LambdaOutput', functions_full_info)
        else:
            functions_parsed_info = []
            for function_info in lambda_function_info_list:
                lambda_info_parsed = self.parse_lambda_info_json_result(function_info)
                functions_parsed_info.append(lambda_info_parsed)
            if output_type == outputType.JSON:
                print('Functions', functions_parsed_info)
            else:
                print(self.get_table(functions_parsed_info))  
            
    def parse_aws_logs(self, logs, request_id):
        if (logs is None) or (request_id is None):
            return None
        full_msg = ""
        logging = False
        lines = logs.split('\n')
        for line in lines:
            if line.startswith('REPORT') and request_id in line:
                full_msg += line + '\n'
                return full_msg
            if logging:
                full_msg += line + '\n'
            if line.startswith('START') and request_id in line:
                full_msg += line + '\n'
                logging = True
    
    def parse_invocation_response(self, response, function_name, output_type, is_asynchronous):
        # Decode and parse the payload
        response = utils.parse_payload(response)
        if "FunctionError" in response:
            if "Task timed out" in response['Payload']:
                # Find the timeout time
                message = utils.find_expression('(Task timed out .* seconds)', str(response['Payload']))
                # Modify the error message
                message = message.replace("Task", "Function '%s'" % function_name)
                if (output_type == outputType.VERBOSE) or (output_type == outputType.JSON):
                    logging.error({"Error" : json.dumps(message)})
                else:
                    logging.error("Error: %s" % message)
            else:
                print("Error in function response")
                logging.error("Error in function response: %s" % response['Payload'])
            utils.finish_failed_execution()
    
        #if self.aws_lambda.is_asynchronous():
        if is_asynchronous:        
            if (output_type == outputType.VERBOSE):
                logging.info('LambdaOutput', response)
            elif (output_type == outputType.JSON):
                logging.info('LambdaOutput', {'StatusCode' : response['StatusCode'],
                                             'RequestId' : response['ResponseMetadata']['RequestId']})
            else:
                logging.info("Function '%s' launched correctly" % function_name)
                print("Function '%s' launched correctly" % function_name)
        else:
            # Transform the base64 encoded results to something legible
            response = utils.parse_base64_response_values(response)
            # Extract log_group_name and log_stream_name from the payload
            response = utils.parse_log_ids(response)
            if (output_type == outputType.VERBOSE):
                logging.info('LambdaOutput', response)
            elif (output_type == outputType.JSON):
                logging.info('LambdaOutput', {'StatusCode' : response['StatusCode'],
                                             'Payload' : response['Payload'],
                                             'LogGroupName' : response['LogGroupName'],
                                             'LogStreamName' : response['LogStreamName'],
                                             'RequestId' : response['ResponseMetadata']['RequestId']})
            else:
                logging.info('SCAR: Request Id: %s' % response['ResponseMetadata']['RequestId'])
                logging.info(response['Payload'])
                print('Request Id: %s' % response['ResponseMetadata']['RequestId'])
                print(response['Payload'])
            
  
    
    def parse_lambda_info_json_result(self, function_info):
        name = function_info['Configuration'].get('FunctionName', "-")
        memory = function_info['Configuration'].get('MemorySize', "-")
        timeout = function_info['Configuration'].get('Timeout', "-")
        image_id = function_info['Configuration']['Environment']['Variables'].get('IMAGE_ID', "-")
        return {'Name' : name,
                'Memory' : memory,
                'Timeout' : timeout,
                'Image_id': image_id}
      
    def get_table(self, functions_info):
        headers = ['NAME', 'MEMORY', 'TIME', 'IMAGE_ID']
        table = []
        for function in functions_info:
            table.append([function['Name'],
                          function['Memory'],
                          function['Timeout'],
                          function['Image_id']])
        return tabulate(table, headers)            