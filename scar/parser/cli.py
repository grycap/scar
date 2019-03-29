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
import scar.exceptions as excp
import scar.logger as logger
import scar.utils as utils
import scar.version as version
import sys

class CommandParser(object):
    
    def __init__(self, scar_cli):
        self.scar_cli = scar_cli
        self.create_parser()
        self.add_subparsers()

    def create_parser(self):
        self.parser = argparse.ArgumentParser(prog="scar",
                                              description="Deploy containers in serverless architectures",
                                              epilog="Run 'scar COMMAND --help' for more information on a command.")
        self.parser.add_argument('--version', help='Show SCAR version.', dest="version", action="store_true", default=False)        

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
        parser_init = self.subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=self.scar_cli.init)
        # Lambda conf
        group = parser_init.add_mutually_exclusive_group(required=True)
        group.add_argument("-i", "--image", help="Container image id (i.e. centos:7)")
        group.add_argument("-if", "--image_file", help="Container image file created with 'docker save' (i.e. centos.tar.gz)")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")
        parser_init.add_argument("-d", "--description", help="Lambda function description.")
        parser_init.add_argument("-n", "--name", help="Lambda function name")
        parser_init.add_argument("-e", "--environment", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_init.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_init.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_init.add_argument("-tt", "--timeout_threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
        parser_init.add_argument("-s", "--init_script", help="Path to the input file passed to the function")
        parser_init.add_argument("-p", "--preheat", help="Preheats the function running it once and downloading the necessary container", action="store_true")
        parser_init.add_argument("-ep", "--extra_payload", help="Folder containing files that are going to be added to the lambda function")
        parser_init.add_argument("-ll", "--log_level", help="Set the log level of the lambda function. Accepted values are: 'CRITICAL','ERROR','WARNING','INFO','DEBUG'", default="INFO")
        # S3 conf
        parser_init.add_argument("-db", "--deployment_bucket", help="Bucket where the deployment package is going to be uploaded.")
        parser_init.add_argument("-ib", "--input_bucket", help="Bucket name where the input files will be stored.")
        parser_init.add_argument("-ob", "--output_bucket", help="Bucket name where the output files are saved.")
        # IAM conf
        parser_init.add_argument("-r", "--iam_role", help="IAM role used in the management of the functions")        
        # SCAR conf
        parser_init.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_init.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        # API Gateway conf        
        parser_init.add_argument("-api", "--api_gateway_name", help="API Gateway name created to launch the lambda function")
        # General AWS conf           
        parser_init.add_argument("-pf", "--profile", help="AWS profile to use")
        parser_init.add_argument("-em", "--execution_mode", help="Specifies the execution mode of the job. It can be 'lambda', 'lambda-batch' or 'batch'")
        
    def add_invoke_parser(self):
        parser_invoke = self.subparsers.add_parser('invoke', help="Call a lambda function using an HTTP request")
        # Set default function
        parser_invoke.set_defaults(func=self.scar_cli.invoke)
        group = parser_invoke.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration") 
        parser_invoke.add_argument("-db", "--data_binary", help="File path of the HTTP data to POST.")
        parser_invoke.add_argument("-jd", "--json_data", help="JSON Body to Post")
        parser_invoke.add_argument("-a", "--asynchronous", help="Launch an asynchronous function.", action="store_true")
        parser_invoke.add_argument("-p", "--parameters", help="In addition to passing the parameters in the URL, you can pass the parameters here (i.e. '{\"key1\": \"value1\", \"key2\": [\"value2\", \"value3\"]}').")
        # General AWS conf          
        parser_invoke.add_argument("-pf", "--profile", help="AWS profile to use")  
 
    def add_update_parser(self):
        parser_update = self.subparsers.add_parser('update', help="Update function properties")
        parser_update.set_defaults(func=self.scar_cli.update)
        group = parser_update.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Update all lambda functions", action="store_true")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")
        parser_update.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_update.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_update.add_argument("-e", "--environment", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_update.add_argument("-tt", "--timeout_threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
        parser_update.add_argument("-ll", "--log_level", help="Set the log level of the lambda function. Accepted values are: 'CRITICAL','ERROR','WARNING','INFO','DEBUG'", default="INFO")
        # General AWS conf        
        parser_update.add_argument("-pf", "--profile", help="AWS profile to use")
        # AWS lambda layers conf         
        parser_update.add_argument("-sl", "--supervisor_layer", help="Update supervisor layer in related functions.", action="store_true")

    def add_run_parser(self):
        parser_run = self.subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=self.scar_cli.run)
        group = parser_run.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")        
        parser_run.add_argument("-a", "--asynchronous", help="Launch an asynchronous function.", action="store_true")
        parser_run.add_argument("-s", "--run_script", help="Path to the input file passed to the function")
        parser_run.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_run.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_run.add_argument('c_args', nargs=argparse.REMAINDER, help="Arguments passed to the container.")
        # General AWS conf
        parser_run.add_argument("-pf", "--profile", help="AWS profile to use")
    
    def add_rm_parser(self):
        parser_rm = self.subparsers.add_parser('rm', help="Delete function")
        parser_rm.set_defaults(func=self.scar_cli.rm)
        group = parser_rm.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Delete all lambda functions", action="store_true")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")        
        parser_rm.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_rm.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        # General AWS conf           
        parser_rm.add_argument("-pf", "--profile", help="AWS profile to use")  
                             
    def add_log_parser(self):
        parser_log = self.subparsers.add_parser('log', help="Show the logs for the lambda function")
        parser_log.set_defaults(func=self.scar_cli.log)
        group = parser_log.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")
        # CloudWatch args       
        parser_log.add_argument("-ls", "--log_stream_name", help="Return the output for the log stream specified.")
        parser_log.add_argument("-ri", "--request_id", help="Return the output for the request id specified.")
        # General AWS conf        
        parser_log.add_argument("-pf", "--profile", help="AWS profile to use")
        
    def add_ls_parser(self):
        parser_ls = self.subparsers.add_parser('ls', help="List lambda functions")
        parser_ls.set_defaults(func=self.scar_cli.ls)
        parser_ls.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_ls.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        # S3 args
        parser_ls.add_argument("-b", "--bucket", help="Show bucket files")
        # Layer args
        parser_ls.add_argument("-l", "--layers", help="Show lambda layers information", action="store_true")
        # General AWS conf        
        parser_ls.add_argument("-pf", "--profile", help="AWS profile to use")                
    
    def add_put_parser(self):
        parser_put = self.subparsers.add_parser('put', help="Upload file(s) to bucket")
        parser_put.set_defaults(func=self.scar_cli.put)
        # S3 args
        parser_put.add_argument("-b", "--bucket", help="Bucket to use as storage", required=True)
        # Local info args
        parser_put.add_argument("-p", "--path", help="Path of the file or folder to upload", required=True)
        # General AWS conf        
        parser_put.add_argument("-pf", "--profile", help="AWS profile to use")
    
    def add_get_parser(self):
        parser_get = self.subparsers.add_parser('get', help="Download file(s) from bucket")
        parser_get.set_defaults(func=self.scar_cli.get)
        # S3 args
        parser_get.add_argument("-b", "--bucket", help="Bucket to use as storage", required=True)
        # Local info args
        parser_get.add_argument("-p", "--path", help="Path to store the downloaded file or folder")
        # General AWS conf
        parser_get.add_argument("-pf", "--profile", help="AWS profile to use")

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
            return utils.merge_dicts(scar_args, aws_args)
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
        self.set_args(aws_args, 'cloudwatch', self.parse_cloudwatchlogs_args(cmd_args))
        self.set_args(aws_args, 's3', self.parse_s3_args(cmd_args))
        self.set_args(aws_args, 'api_gateway', self.parse_api_gateway_args(cmd_args))
        aws_args.update(utils.parse_arg_list(other_args, cmd_args))
        return {'aws' : aws_args }

    def parse_scar_args(self, cmd_args):
        scar_args = ['func', 'conf_file', 'json', 'verbose', 'path', 'all', 'preheat', 'execution_mode',]
        return {'scar' : utils.parse_arg_list(scar_args, cmd_args)}

    def parse_lambda_args(self, cmd_args):
        lambda_args = ['name', 'asynchronous', 'init_script', 'run_script', 'c_args', 'memory', 'time',
                       'timeout_threshold', 'log_level', 'image', 'image_file', 'description', 
                       'lambda_role', 'extra_payload', ('environment', 'environment_variables'),
                       'layers', 'supervisor_layer']
        return utils.parse_arg_list(lambda_args, cmd_args)
    
    def parse_iam_args(self, cmd_args):
        iam_args = [('iam_role', 'role')]
        return utils.parse_arg_list(iam_args, cmd_args)    
    
    def parse_cloudwatchlogs_args(self, cmd_args):
        cw_log_args = ['log_stream_name', 'request_id']
        return utils.parse_arg_list(cw_log_args, cmd_args)
    
    def parse_api_gateway_args(self, cmd_args):
        api_gtw_args = [('api_gateway_name', 'name'), 'parameters', 'data_binary', 'json_data']
        return utils.parse_arg_list(api_gtw_args, cmd_args)     
        
    def parse_s3_args(self, cmd_args):
        s3_args = ['deployment_bucket', 
                   'input_bucket', 
                   'output_bucket', 
                   ('bucket', 'input_bucket'), 
                   ]
        return utils.parse_arg_list(s3_args, cmd_args)        
        
