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

from scar.exceptions import ValidatorError, S3CodeSizeError, FunctionCodeSizeError, InvocationPayloadError
from scar.validator import GenericValidator
import os
import scar.utils as utils

VALID_LAMBDA_NAME_REGEX = "(arn:(aws[a-zA-Z-]*)?:lambda:)?([a-z]{2}(-gov)?-[a-z]+-\d{1}:)?(\d{12}:)?(function:)?([a-zA-Z0-9-_]+)(:(\$LATEST|[a-zA-Z0-9-_]+))?"
KB = 1024
MB = KB*KB
MAX_POST_BODY_SIZE = MB*6
MAX_POST_BODY_SIZE_ASYNC = KB*95

class AWSValidator(GenericValidator):
    
    @classmethod
    def validate_kwargs(cls, **kwargs):
        prov_args = kwargs['aws']
        if 'iam' in prov_args:
            cls.validate_iam(prov_args['iam'])     
        if 'lambda' in prov_args:
            cls.validate_lambda(prov_args['lambda']) 
    
    @staticmethod
    def validate_iam(iam_properties):
        if ("role" not in iam_properties) or (iam_properties["role"] == ""):
            error_msg="Please, specify a valid iam role in the configuration file (usually located in ~/.scar/scar.cfg)."
            raise ValidatorError(parameter='iam_role', parameter_value=iam_properties, error_msg=error_msg)
    
    @classmethod
    def validate_lambda(cls, lambda_properties):
        if 'name' in lambda_properties:
            cls.validate_function_name(lambda_properties['name'])
        if 'memory' in lambda_properties:
            cls.validate_memory(lambda_properties['memory'])
        if 'time' in lambda_properties:
            cls.validate_time(lambda_properties['time']) 
    
    @staticmethod
    def validate_time(lambda_time):
        if (lambda_time <= 0) or (lambda_time > 300):
            error_msg = 'Please, set a value between 0 and 300.'
            raise ValidatorError(parameter='lambda_time', parameter_value=lambda_time, error_msg=error_msg)
    
    @staticmethod
    def validate_memory(lambda_memory):
        if (lambda_memory < 128) or (lambda_memory > 3008):
            error_msg = 'Please, set a value between 128 and 3008.'
            raise ValidatorError(parameter='lambda_memory', parameter_value=lambda_memory, error_msg=error_msg)

    @staticmethod            
    def validate_function_name(function_name):
        if not utils.find_expression(function_name, VALID_LAMBDA_NAME_REGEX):
            error_msg = 'Find name restrictions in: https://docs.aws.amazon.com/lambda/latest/dg/API_CreateFunction.html#SSS-CreateFunction-request-FunctionName'
            raise ValidatorError(parameter='function_name', parameter_value=function_name, error_msg=error_msg)
    
    @staticmethod
    def validate_function_code_size(code_file_path, MAX_PAYLOAD_SIZE):
        if os.path.getsize(code_file_path) > MAX_PAYLOAD_SIZE:
            raise FunctionCodeSizeError(code_size='50MB')
        
    @staticmethod        
    def validate_s3_code_size(scar_folder, MAX_S3_PAYLOAD_SIZE):
        if utils.get_tree_size(scar_folder) > MAX_S3_PAYLOAD_SIZE:         
            raise S3CodeSizeError(code_size='250MB')
        
    @staticmethod        
    def validate_http_payload_size(file_path, async_call=False):        
        file_size = utils.get_file_size(file_path)
        if file_size > MAX_POST_BODY_SIZE:
            filesize = '{0:.2f}MB'.format(file_size/MB)
            maxsize = '{0:.2f}MB'.format(MAX_POST_BODY_SIZE/MB)            
            raise InvocationPayloadError(file_size= filesize, max_size=maxsize)
        elif async_call and file_size > MAX_POST_BODY_SIZE_ASYNC:
            filesize = '{0:.2f}KB'.format(file_size/KB)
            maxsize = '{0:.2f}KB'.format(MAX_POST_BODY_SIZE_ASYNC/KB)
            raise InvocationPayloadError(file_size=filesize, max_size=maxsize)        
            