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
""" Module containing all the custom exceptions for SCAR. """

import functools
import sys
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

            except ClientError as cerr:
                print(f"There was an exception in {func.__name__}")
                print(cerr.response['Error']['Message'])
                logger.exception(cerr)
                sys.exit(1)

            except ScarError as serr:
                print(serr.args[0])
                logger.exception(serr)
                # Finish the execution if it's an error
                if 'Error' in serr.__class__.__name__:
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
class MissingCommandError(ScarError):
    """
    SCAR was launched without a command

    """
    fmt = ("Please use one of the scar available commands "
           "(init,invoke,run,update,rm,ls,log,put,get)")


class ScarConfigFileError(ScarError):
    """
    The SCAR configuration file does not exist and it has been created

    :ivar file_path: Path of the file
    """
    fmt = ("Config file '{file_path}' created.\n"
           "Please, set a valid iam role in the file field 'role' before the first execution.")


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


class FdlFileNotFoundError(ScarError):
    """
    The configuration file does not exist

    :ivar file_path: Path of the file
    """
    fmt = "Unable to find the configuration file '{file_path}'"


class ValidatorError(ScarError):
    """
    An error occurred when validating a parameter

    :ivar parameter: Name of the parameter evaluated
    :ivar parameter_value: Current value of the validated parameter
    :ivar error_msg: General error message
    """
    fmt = ("Error validating '{parameter}'.\n"
           "Value '{parameter_value}' incorrect.\n"
           "{error_msg}")


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
    fmt = ("Payload size greater than {code_size}.\n"
           "Please reduce the payload size or use an S3 bucket and try again.")


class S3CodeSizeError(ScarError):
    """
    Function code uploaded to S3 exceeds AWS limits

    :ivar code_size: Name of the parameter evaluated
    """

    fmt = ("Uncompressed image size greater than {code_size}.\n"
           "Please reduce the uncompressed image and try again.")


class GitHubTagNotFoundError(ScarError):
    """
    The specified tag was not found in the GitHub repository

    :ivar version: Tag used for the search
    """

    fmt = "The tag '{tag}' was not found in the GitHub repository."


class StorageProviderNotSupportedError(ScarError):
    """
    The storage provider parsed is not supported

    :ivar provider: Provider specified
    """
    fmt = "The storage provider '{provider}' is not supported."


class AuthenticationVariableNotSupportedError(ScarError):
    """
    The authentication variable parsed is not supported

    :ivar auth_var: Authentication variable specified
    """
    fmt = "The authentication variable '{auth_var}' is not supported."

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
    fmt = ("Error retrieving API ID for lambda function '{function_name}'\n"
           "Looks like he requested function does not have an associated API.")


class InvocationPayloadError(ScarError):
    """
    Error invocating the API endpoint.

    :ivar file_size: Size of the passed file
    :ivar max_size: Max size allowd of the file
    """
    fmt = ("Invalid request: Payload size {file_size} greater than {max_size}\n"
           "Check AWS Lambda invocation limits in : "
           "https://docs.aws.amazon.com/lambda/latest/dg/limits.html")


class NotExistentApiGatewayWarning(ScarError):
    """
    The API with the id 'restApiId' was not found.

    :ivar bucket_name: Name of the bucket
    """
    fmt = "The requested API '{restApiId}' does not exist."


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


################################################
##              OSCAR EXCEPTIONS              ##
################################################
class ServiceCreationError(ScarError):
    """
    There was an error creating the OSCAR service

    :ivar service_name: Name of the function
    :ivar error_msg: General error message
    """
    fmt = "Unable to create the service '{service_name}': {error_msg}"


class ServiceDeletionError(ScarError):
    """
    There was an error deleting the OSCAR service

    :ivar service_name: Name of the function
    :ivar error_msg: General error message
    """
    fmt = "Unable to delete the service '{service_name}': {error_msg}"

class ServiceNotFoundError(ScarError):
    """
    There was an error getting the OSCAR service

    :ivar service_name: Name of the function
    :ivar error_msg: General error message
    """
    fmt = "The service '{service_name}' does not exist: {error_msg}"

class ListServicesError(ScarError):
    """
    There was an error getting the OSCAR service

    :ivar service_name: Name of the function
    :ivar error_msg: General error message
    """
    fmt = "Unable to list services from OSCAR cluster '{cluster_id}': {error_msg}"