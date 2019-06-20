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

import argparse
import sys
import scar.exceptions as excp
import scar.logger as logger
from scar.utils import DataTypesUtils
import scar.version as version


class CommandParser(object):
    
    def __init__(self, scar_cli):
        self.scar_cli = scar_cli
        self.create_parser()
        self.create_parent_parsers()
        self.add_subparsers()

    def create_parser(self):
        self.parser = argparse.ArgumentParser(prog="scar",
                                              description="Deploy containers in serverless architectures",
                                              epilog="Run 'scar COMMAND --help' for more information on a command.")
        self.parser.add_argument('--version', help='Show SCAR version.', dest="version", action="store_true", default=False)

    def create_parent_parsers(self):
        self.create_function_definition_parser()
        self.create_exec_parser()
        self.create_output_parser()
        self.create_profile_parser()
        self.create_storage_parser()

    def create_function_definition_parser(self):
        self.function_definition_parser = argparse.ArgumentParser(add_help=False)
        self.function_definition_parser.add_argument("-d", "--description", help="Lambda function description.")
        self.function_definition_parser.add_argument("-e", "--environment", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        self.function_definition_parser.add_argument("-le", "--lambda-environment", action='append', help="Pass environment variable to the lambda function (VAR=val). Can be defined multiple times.")
        self.function_definition_parser.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 3008 in increments of 64")
        self.function_definition_parser.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 900.")
        self.function_definition_parser.add_argument("-tt", "--timeout-threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
        self.function_definition_parser.add_argument("-ll", "--log-level", help="Set the log level of the lambda function. Accepted values are: 'CRITICAL','ERROR','WARNING','INFO','DEBUG'", default="INFO")
        self.function_definition_parser.add_argument("-l", "--layers", action='append', help="Pass layers ARNs to the lambda function. Can be defined multiple times.")
        self.function_definition_parser.add_argument("-ib", "--input-bucket", help="Bucket name where the input files will be stored.")
        self.function_definition_parser.add_argument("-ob", "--output-bucket", help="Bucket name where the output files are saved.")
        self.function_definition_parser.add_argument("-em", "--execution-mode", help="Specifies the execution mode of the job. It can be 'lambda', 'lambda-batch' or 'batch'")
        self.function_definition_parser.add_argument("-r", "--iam-role", help="IAM role used in the management of the functions")
        self.function_definition_parser.add_argument("-sv", "--supervisor-version", help="FaaS Supervisor version. Can be a tag or 'latest'.")
        # Batch (job definition) options
        self.function_definition_parser.add_argument("-bm", "--batch-memory", help="Batch job memory in megabytes")
        self.function_definition_parser.add_argument("-bc", "--batch-vcpus", help="Number of vCPUs reserved for the Batch container")
        self.function_definition_parser.add_argument("-g", "--enable-gpu", help="Reserve one physical GPU for the Batch container (if it's available in the compute environment)", action="store_true")

    def create_exec_parser(self):
        self.exec_parser = argparse.ArgumentParser(add_help=False)
        self.exec_parser.add_argument("-a", "--asynchronous", help="Launch an asynchronous function.", action="store_true")
        self.exec_parser.add_argument("-o", "--output-file", help="Save output as a file")  

    def create_output_parser(self):
        self.output_parser = argparse.ArgumentParser(add_help=False)
        self.output_parser.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        self.output_parser.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")

    def create_profile_parser(self):
        self.profile_parser = argparse.ArgumentParser(add_help=False)
        self.profile_parser.add_argument("-pf", "--profile", help="AWS profile to use")

    def create_storage_parser(self):
        self.storage_parser = argparse.ArgumentParser(add_help=False)
        self.storage_parser.add_argument("-b", "--bucket", help="Bucket to use as storage", required=True)
        self.storage_parser.add_argument("-p", "--path", help="Path of the file or folder", required=True)

    def add_subparsers(self):
        self.subparsers = self.parser.add_subparsers(title='Commands')    
        self.add_init_parser()
        self.add_invoke_parser()
        self.add_run_parser()
        self.add_update_parser()
        self.add_rm_parser()
        self.add_ls_parser()
        self.add_log_parser()
        self.add_put_parser()
        self.add_get_parser()
    
    def add_init_parser(self):
        parser_init = self.subparsers.add_parser('init', parents=[self.function_definition_parser, self.output_parser, self.profile_parser], help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=self.scar_cli.init)
        # Lambda conf
        group = parser_init.add_mutually_exclusive_group(required=True)
        group.add_argument("-i", "--image", help="Container image id (i.e. centos:7)")
        group.add_argument("-if", "--image-file", help="Container image file created with 'docker save' (i.e. centos.tar.gz)")
        group.add_argument("-f", "--conf-file", help="Yaml file with the function configuration")
        parser_init.add_argument("-n", "--name", help="Lambda function name")
        parser_init.add_argument("-s", "--init-script", help="Path to the input file passed to the function")
        parser_init.add_argument("-ph", "--preheat", help="Preheats the function running it once and downloading the necessary container", action="store_true")
        parser_init.add_argument("-ep", "--extra-payload", help="Folder containing files that are going to be added to the lambda function")
        parser_init.add_argument("-db", "--deployment-bucket", help="Bucket where the deployment package is going to be uploaded.")    
        # API Gateway conf        
        parser_init.add_argument("-api", "--api-gateway-name", help="API Gateway name created to launch the lambda function")
        
    def add_invoke_parser(self):
        parser_invoke = self.subparsers.add_parser('invoke', parents=[self.profile_parser, self.exec_parser], help="Call a lambda function using an HTTP request")
        # Set default function
        parser_invoke.set_defaults(func=self.scar_cli.invoke)
        group = parser_invoke.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf-file", help="Yaml file with the function configuration") 
        parser_invoke.add_argument("-db", "--data-binary", help="File path of the HTTP data to POST.")
        parser_invoke.add_argument("-jd", "--json-data", help="JSON Body to Post")
        parser_invoke.add_argument("-p", "--parameters", help="In addition to passing the parameters in the URL, you can pass the parameters here (i.e. '{\"key1\": \"value1\", \"key2\": [\"value2\", \"value3\"]}').")
 
    def add_update_parser(self):
        parser_update = self.subparsers.add_parser('update', parents=[self.function_definition_parser, self.output_parser, self.profile_parser], help="Update function properties")
        parser_update.set_defaults(func=self.scar_cli.update)
        group = parser_update.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Update all lambda functions", action="store_true")
        group.add_argument("-f", "--conf-file", help="Yaml file with the function configuration")

    def add_run_parser(self):
        parser_run = self.subparsers.add_parser('run', parents=[self.output_parser, self.profile_parser, self.exec_parser], help="Deploy function")
        parser_run.set_defaults(func=self.scar_cli.run)
        group = parser_run.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf-file", help="Yaml file with the function configuration")        
        parser_run.add_argument("-s", "--run-script", help="Path to the input file passed to the function")
        parser_run.add_argument('c_args', nargs=argparse.REMAINDER, help="Arguments passed to the container.")     
    
    def add_rm_parser(self):
        parser_rm = self.subparsers.add_parser('rm', parents=[self.output_parser, self.profile_parser], help="Delete function")
        parser_rm.set_defaults(func=self.scar_cli.rm)
        group = parser_rm.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Delete all lambda functions", action="store_true")
        group.add_argument("-f", "--conf-file", help="Yaml file with the function configuration")        
                             
    def add_log_parser(self):
        parser_log = self.subparsers.add_parser('log', parents=[self.profile_parser], help="Show the logs for the lambda function")
        parser_log.set_defaults(func=self.scar_cli.log)
        group = parser_log.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf-file", help="Yaml file with the function configuration")
        # CloudWatch args       
        parser_log.add_argument("-ls", "--log-stream-name", help="Return the output for the log stream specified.")
        parser_log.add_argument("-ri", "--request-id", help="Return the output for the request id specified.")
        
    def add_ls_parser(self):
        parser_ls = self.subparsers.add_parser('ls', parents=[self.output_parser, self.profile_parser], help="List lambda functions")
        parser_ls.set_defaults(func=self.scar_cli.ls)
        # S3 args
        parser_ls.add_argument("-b", "--bucket", help="Show bucket files")
        # Layer args
        parser_ls.add_argument("-l", "--list-layers", help="Show lambda layers information", action="store_true")             
    
    def add_put_parser(self):
        parser_put = self.subparsers.add_parser('put', parents=[self.storage_parser, self.profile_parser], help="Upload file(s) to bucket")
        parser_put.set_defaults(func=self.scar_cli.put)
    
    def add_get_parser(self):
        parser_get = self.subparsers.add_parser('get', parents=[self.storage_parser, self.profile_parser], help="Download file(s) from bucket")
        parser_get.set_defaults(func=self.scar_cli.get)

    @excp.exception(logger)
    def parse_arguments(self):
        '''Command parsing and selection'''
        try:
            cmd_args = self.parser.parse_args()
            if cmd_args.version:
                print("SCAR {}".format(version.__version__))
                sys.exit(0)                 
            
            cmd_args = vars(cmd_args)
            if 'func' not in cmd_args:
                raise excp.MissingCommandError()
            scar_args = self.parse_scar_args(cmd_args)
            aws_args = self.parse_aws_args(cmd_args)
            return DataTypesUtils.merge_dicts(scar_args, aws_args)
        except AttributeError as ae:
            logger.error("Incorrect arguments: use scar -h to see the options available",
                             "Error parsing arguments: {}".format(ae))
        else:
            raise
        
    def set_args(self, args, key, val):
        if key and val:
            args[key] = val
        
    def parse_aws_args(self, cmd_args):
        aws_args = {}
        other_args = [('profile','boto_profile'),'region','execution_mode']
        self.set_args(aws_args, 'iam', self.parse_iam_args(cmd_args))
        self.set_args(aws_args, 'lambda', self.parse_lambda_args(cmd_args))
        self.set_args(aws_args, 'batch', self.parse_batch_args(cmd_args))
        self.set_args(aws_args, 'cloudwatch', self.parse_cloudwatchlogs_args(cmd_args))
        self.set_args(aws_args, 's3', self.parse_s3_args(cmd_args))
        self.set_args(aws_args, 'api_gateway', self.parse_api_gateway_args(cmd_args))
        aws_args.update(DataTypesUtils.parse_arg_list(other_args, cmd_args))
        return {'aws' : aws_args}

    def parse_scar_args(self, cmd_args):
        scar_args = ['func', 'conf_file', 'json',
                     'verbose', 'path', 'all',
                     'preheat', 'execution_mode',
                     'output_file', 'supervisor_version']
        return {'scar' : DataTypesUtils.parse_arg_list(scar_args, cmd_args)}

    def parse_lambda_args(self, cmd_args):
        lambda_args = ['name', 'asynchronous', 'init_script', 'run_script', 'c_args', 'memory', 'time',
                       'timeout_threshold', 'log_level', 'image', 'image_file', 'description', 
                       'lambda_role', 'extra_payload', ('environment', 'environment_variables'),
                       'layers', 'lambda_environment', 'list_layers']
        return DataTypesUtils.parse_arg_list(lambda_args, cmd_args)

    def parse_batch_args(self, cmd_args):
        batch_args = [('batch_vcpus', 'vcpus'), ('batch_memory', 'memory'), 'enable_gpu']
        return DataTypesUtils.parse_arg_list(batch_args, cmd_args)

    def parse_iam_args(self, cmd_args):
        iam_args = [('iam_role', 'role')]
        return DataTypesUtils.parse_arg_list(iam_args, cmd_args)    
    
    def parse_cloudwatchlogs_args(self, cmd_args):
        cw_log_args = ['log_stream_name', 'request_id']
        return DataTypesUtils.parse_arg_list(cw_log_args, cmd_args)
    
    def parse_api_gateway_args(self, cmd_args):
        api_gtw_args = [('api_gateway_name', 'name'), 'parameters', 'data_binary', 'json_data']
        return DataTypesUtils.parse_arg_list(api_gtw_args, cmd_args)     
        
    def parse_s3_args(self, cmd_args):
        s3_args = ['deployment_bucket', 
                   'input_bucket', 
                   'output_bucket', 
                   ('bucket', 'input_bucket'), 
                   ]
        return DataTypesUtils.parse_arg_list(s3_args, cmd_args)        
