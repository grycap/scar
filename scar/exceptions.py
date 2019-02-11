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

from botocore.exceptions import ClientError
import functools
import sys

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
                sys.exit(1)
            except ScarError as se:
                print(se.args[0])
                logger.exception(se)
                # Finish the execution if it's an error
                if 'Error' in se.__class__.__name__:
                    sys.exit(1)
            except Exception as ex:
                print("There was an unmanaged exception in {0}".format(func.__name__))
                logger.exception(ex)
                sys.exit(1)
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
class InvalidPlatformError(ScarError):
    """
    SCAR binary is not launched on a Linux platform

    """
    fmt = "The SCAR binary only works on a Linux Platform.\nTry executing the Python version."

class MissingCommandError(ScarError):
    """
    SCAR was launched without a command

    """
    fmt = "Please use one of the scar available commands (init,invoke,run,update,rm,ls,log,put,get)"
    
class ScarConfigFileError(ScarError):
    """
    The SCAR configuration file does not exist and it has been created

    :ivar file_path: Path of the file
    """
    fmt = "Config file '{file_path}' created.\n"
    fmt += "Please, set a valid iam role in the file field 'role' before the first execution."    

class UploadFileNotFoundError(ScarError):
    """
    The file does not exist

    :ivar file_path: Path of the file
    """
    fmt = "Unable to find the file to upload with path '{file_path}'"
                
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

class ScarFunctionNotFoundError(ScarError):
    """
    The called function was not found

    :ivar func_name: Name of the function called
    """
    fmt = "Unable to find the function '{func_name}'"

class FunctionCodeSizeError(ScarError):
    """
    Function code size exceeds AWS limits

    :ivar code_size: Name of the parameter evaluated
    """
    fmt = "Payload size greater than {code_size}.\nPlease reduce the payload size or use an S3 bucket and try again."

class S3CodeSizeError(ScarError):
    """
    Function code uploaded to S3 exceeds AWS limits

    :ivar code_size: Name of the parameter evaluated
    """
    
    fmt = "Uncompressed image size greater than {code_size}.\nPlease reduce the uncompressed image and try again."

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
    """
    fmt = "Unable to find the function '{function_name}'"
    
class FunctionExistsError(ScarError):
    """
    The requested function exists.

    :ivar function_name: Name of the function
    """
    fmt = "Function '{function_name}' already exists"    

################################################
##               S3 EXCEPTIONS                ##
################################################
class BucketNotFoundError(ScarError):
    """
    The requested bucket does not exist.

    :ivar bucket_name: Name of the bucket
    """
    fmt = "Unable to find the bucket '{bucket_name}'."
    
class ExistentBucketWarning(ScarError):
    """
    The bucket already exists

    :ivar bucket_name: Name of the bucket
    """
    fmt = "Using existent bucket '{bucket_name}'."    
    
################################################
##         CLOUDWATCH LOGS EXCEPTIONS         ##
################################################
class ExistentLogGroupWarning(ScarError):
    """
    The requested log group already exists

    :ivar log_group_name: Name of the log group
    """
    fmt = "Using existent log group '{logGroupName}'."
    
class NotExistentLogGroupWarning(ScarError):
    """
    The requested log group does not exists

    :ivar log_group_name: Name of the log group
    """
    fmt = "The requested log group '{logGroupName}' does not exist."
    
################################################
##           API GATEWAY EXCEPTIONS           ##
################################################
class ApiEndpointNotFoundError(ScarError):
    """
    The requested function does not have an associated API.

    :ivar function_name: Name of the function
    """
    fmt = "Error retrieving API ID for lambda function '{function_name}'\n"
    fmt += "Looks like he requested function does not have an associated API."
    
class ApiCreationError(ScarError):
    """
    Error creating the API endpoint.

    :ivar api_name: Name of the api
    """
    fmt = "Error creating the API '{api_name}'"
    
class InvocationPayloadError(ScarError):
    """
    Error invocating the API endpoint.

    :ivar file_size: Size of the passed file
    :ivar max_size: Max size allowd of the file
    """
    fmt = "Invalid request: Payload size {file_size} greater than {max_size}\n"
    fmt += "Check AWS Lambda invocation limits in : https://docs.aws.amazon.com/lambda/latest/dg/limits.html"
    
################################################
##               IAM EXCEPTIONS               ##
################################################
class GetUserInfoError(ScarError):
    """
    There was an error gettting the IAM user info

    :ivar error_msg: General error message    
    """
    fmt = "Error getting the AWS user information.\n{error_msg}."
    
################################################
##              BATCH EXCEPTIONS              ##
################################################
class InvalidComputeEnvironmentError(ScarError):
    """
    There was an error creating the Batch Compute Environment

    :ivar error_msg: General error message    
    """
    fmt = "Error creating the AWS Batch Compute Environment\n."
    
    