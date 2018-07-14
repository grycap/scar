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
from src.exceptions import ValidatorError
from src.validator import GenericValidator

valid_lambda_name_regex = "(arn:(aws[a-zA-Z-]*)?:lambda:)?([a-z]{2}(-gov)?-[a-z]+-\d{1}:)?(\d{12}:)?(function:)?([a-zA-Z0-9-_]+)(:(\$LATEST|[a-zA-Z0-9-_]+))?"

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
        if not utils.find_expression(function_name, valid_lambda_name_regex):
            error_msg = 'Find name restrictions in: https://docs.aws.amazon.com/lambda/latest/dg/API_CreateFunction.html#SSS-CreateFunction-request-FunctionName'
            raise ValidatorError(parameter='function_name', parameter_value=function_name, error_msg=error_msg)
            