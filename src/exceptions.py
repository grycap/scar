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

import functools
from botocore.exceptions import ClientError

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
                exit(1)
            except ScarError as se:
                #print("There was an exception in {0}".format(func.__name__))
                print(se.args[0])
                logger.exception(se)
                exit(1)                
            except Exception as ex:
                print("There was an unmanaged exception in {0}".format(func.__name__))
                logger.exception(ex)
                exit(1)
        return wrapper
    return decorator

class ScarError(Exception):
    """
    The base exception class for ScarError exceptions.

    :ivar msg: The descriptive message associated with the error.
    """
    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs

################################################
##             GENERAL EXCEPTIONS             ##
################################################                   
class YamlFileNotFoundError(ScarError):
    """
    The yaml configuration file does not exist

    :ivar file_path: Path of the file
    """
    fmt = "Unable to find the yaml file '{file_path}'"
    
class ValidatorError(ScarError):
    """
    An error occurred when validating a parameter

    :ivar parameter: Name of the parameter evaluated
    :ivar parameter_value: Current value of the validated parameter
    :ivar error_msg: General error message
    """
    fmt = "Error validating '{parameter}'.\nValue '{parameter_value}' incorrect.\n{error_msg}"

################################################
##             LAMBDA EXCEPTIONS              ##
################################################
class FunctionCreationError(ScarError):
    """
    An error occurred when creating the lambda function.

    :ivar function_name: Name of the function
    :ivar error_msg: General error message    
    """
    fmt = "Unable to create the function '{function_name}' : {error_msg}"        

class FunctionNotFoundError(ScarError):
    """
    The requested function does not exist.

    :ivar function_name: Name of the function
    :ivar error_msg: General error message    
    """
    fmt = "Unable to find the function '{function_name}' : {error_msg}"

################################################
##               S3 EXCEPTIONS                ##
################################################
class BucketNotFoundError(ScarError):
    """
    The requested bucket does not exist.

    :ivar bucket_name: Name of the bucket
    :ivar error_msg: General error message    
    """
    fmt = "Unable to find the bucket '{bucket_name}'."
    