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

import argparse
import src.logger as logger
import src.utils as utils

class CommandParser(object):
    
    def __init__(self, scar):
        self.scar = scar
        self.create_parser()
        self.create_subparsers()

    def create_parser(self):
        self.parser = argparse.ArgumentParser(prog="scar",
                                              description="Deploy containers in serverless architectures",
                                              epilog="Run 'scar COMMAND --help' for more information on a command.")

    def create_subparsers(self):
        self.subparsers = self.parser.add_subparsers(title='Commands')    
        self.create_init_parser()
        self.create_invoke_parser()
        self.create_run_parser()
        self.create_update_parser()
        self.create_rm_parser()
        self.create_ls_parser()
        self.create_log_parser()
        self.create_put_parser()
        self.create_get_parser()        
    
    def create_init_parser(self):
        parser_init = self.subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=self.scar.init)
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
        # parser_init.add_argument("-out-func", "--output_function", help="Function name where the output will be redirected")
        # S3 conf
        parser_init.add_argument("-db", "--deployment_bucket", help="Bucket where the deployment package is going to be uploaded.")
        parser_init.add_argument("-ib", "--input_bucket", help="Bucket name where the input files will be stored.")
        parser_init.add_argument("-inf", "--input_folder", help="Folder name where the input files will be stored (Only works when an input bucket is defined).")
        parser_init.add_argument("-ob", "--output_bucket", help="Bucket name where the output files are saved.")
        parser_init.add_argument("-outf", "--output_folder", help="Folder name where the output files are saved (Only works when an input bucket is defined).")
        # IAM conf
        parser_init.add_argument("-r", "--iam_role", help="IAM role used in the management of the functions")        
        # SCAR conf
        parser_init.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_init.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")        
        # API Gateway conf        
        parser_init.add_argument("-api", "--api_gateway_name", help="API Gateway name created to launch the lambda function")
        # General AWS conf           
        parser_init.add_argument("-pf", "--profile", help="AWS profile to use")
        
    def create_invoke_parser(self):
        parser_invoke = self.subparsers.add_parser('invoke', help="Call a lambda function using an HTTP request")
        # Set default function
        parser_invoke.set_defaults(func=self.scar.invoke)
        group = parser_invoke.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration") 
        parser_invoke.add_argument("-db", "--data_binary", help="File path of the HTTP data to POST.")
        parser_invoke.add_argument("-a", "--asynchronous", help="Launch an asynchronous function.", action="store_true")
        parser_invoke.add_argument("-p", "--parameters", help="In addition to passing the parameters in the URL, you can pass the parameters here (i.e. '{\"key1\": \"value1\", \"key2\": [\"value2\", \"value3\"]}').")
        # General AWS conf          
        parser_invoke.add_argument("-pf", "--profile", help="AWS profile to use")  
 
    def create_update_parser(self):
        parser_update = self.subparsers.add_parser('update', help="Update function properties")
        parser_update.set_defaults(func=self.scar.update)
        group = parser_update.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")        
        parser_update.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_update.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_update.add_argument("-e", "--environment", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_update.add_argument("-tt", "--timeout_threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
        parser_update.add_argument("-ll", "--log_level", help="Set the log level of the lambda function. Accepted values are: 'CRITICAL','ERROR','WARNING','INFO','DEBUG'", default="INFO")
        # General AWS conf        
        parser_update.add_argument("-pf", "--profile", help="AWS profile to use")        
        #parser_update.add_argument("-s", "--script", nargs='?', type=argparse.FileType('r'), help="Path to the input file passed to the function")
        #parser_update.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        #parser_update.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        #parser_update.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
    
    def create_run_parser(self):
        parser_run = self.subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=self.scar.run)
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
    
    def create_rm_parser(self):
        parser_rm = self.subparsers.add_parser('rm', help="Delete function")
        parser_rm.set_defaults(func=self.scar.rm)
        group = parser_rm.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Delete all lambda functions", action="store_true")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")        
        parser_rm.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_rm.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        # General AWS conf           
        parser_rm.add_argument("-pf", "--profile", help="AWS profile to use")  
                             
    def create_log_parser(self):
        parser_log = self.subparsers.add_parser('log', help="Show the logs for the lambda function")
        parser_log.set_defaults(func=self.scar.log)
        group = parser_log.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf_file", help="Yaml file with the function configuration")
        # CloudWatch args       
        parser_log.add_argument("-ls", "--log_stream_name", help="Return the output for the log stream specified.")
        parser_log.add_argument("-ri", "--request_id", help="Return the output for the request id specified.")
        # General AWS conf        
        parser_log.add_argument("-pf", "--profile", help="AWS profile to use")
        
    def create_ls_parser(self):
        parser_ls = self.subparsers.add_parser('ls', help="List lambda functions")
        parser_ls.set_defaults(func=self.scar.ls)
        parser_ls.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_ls.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        # S3 args
        parser_ls.add_argument("-b", "--bucket", help="Show bucket files")
        parser_ls.add_argument("-bf", "--bucket_folder", help="Show bucket files")
        # General AWS conf        
        parser_ls.add_argument("-pf", "--profile", help="AWS profile to use")                
    
    def create_put_parser(self):
        parser_put = self.subparsers.add_parser('put', help="Upload file(s) to bucket")
        parser_put.set_defaults(func=self.scar.put)
        # S3 args
        parser_put.add_argument("-b", "--bucket", help="Bucket to use as storage", required=True)
        parser_put.add_argument("-bf", "--bucket_folder", help="Folder used to store the file(s) in the bucket")
        # Local info args
        parser_put.add_argument("-p", "--path", help="Path of the file or folder to upload", required=True)
        # General AWS conf        
        parser_put.add_argument("-pf", "--profile", help="AWS profile to use")
    
    def create_get_parser(self):
        parser_get = self.subparsers.add_parser('get', help="Download file(s) from bucket")
        parser_get.set_defaults(func=self.scar.get)
        # S3 args
        parser_get.add_argument("-b", "--bucket", help="Bucket to use as storage", required=True)
        parser_get.add_argument("-bf", "--bucket_folder", help="Path of the file or folder to download")
        # Local info args
        parser_get.add_argument("-p", "--path", help="Path to store the downloaded file or folder")
        # General AWS conf
        parser_get.add_argument("-pf", "--profile", help="AWS profile to use")

    def parse_arguments(self):
        '''Command parsing and selection'''
        try:
            cmd_args = vars(self.parser.parse_args())
            scar_args = self.parse_scar_args(cmd_args)
            aws_args = self.parse_aws_args(cmd_args)
            return utils.merge_dicts(scar_args, aws_args)
        except AttributeError as ae:
            logger.error("Incorrect arguments: use scar -h to see the options available",
                             "Error parsing arguments: %s" % ae)            
            raise
        
    def set_args(self, args, key, val):
        if val:
            args[key] = val
        
    def parse_aws_args(self, cmd_args):
        aws_args = {}
        other_args = [('profile','boto_profile'),'region']
        self.set_args(aws_args, 'iam', self.parse_iam_args(cmd_args))
        self.set_args(aws_args, 'lambda', self.parse_lambda_args(cmd_args))
        self.set_args(aws_args, 'cloudwatch', self.parse_cloudwatchlogs_args(cmd_args))
        self.set_args(aws_args, 's3', self.parse_s3_args(cmd_args))
        self.set_args(aws_args, 'api_gateway', self.parse_api_gateway_args(cmd_args))
        aws_args.update(utils.parse_arg_list(other_args, cmd_args))
        aws = {}
        aws['aws'] = aws_args
        return aws

    def parse_scar_args(self, cmd_args):
        scar_args = ['func', 'conf_file', 'json', 'verbose', 'path', ('all', 'delete_all'), 'preheat']
        scar = {}
        scar['scar'] = utils.parse_arg_list(scar_args, cmd_args)
        return scar

    def parse_lambda_args(self, cmd_args):
        lambda_args = ['name', 'asynchronous', 'init_script', 'run_script', 'c_args', 'memory', 'time',
                       'timeout_threshold', 'log_level', 'image', 'image_file', 'description', 
                       'lambda_role', 'extra_payload', ('environment', 'environment_variables')]
        return utils.parse_arg_list(lambda_args, cmd_args)
    
    def parse_iam_args(self, cmd_args):
        iam_args = [('iam_role', 'role')]
        return utils.parse_arg_list(iam_args, cmd_args)    
    
    def parse_cloudwatchlogs_args(self, cmd_args):
        cw_log_args = ['log_stream_name', 'request_id']
        return utils.parse_arg_list(cw_log_args, cmd_args)
    
    def parse_api_gateway_args(self, cmd_args):
        api_gtw_args = [('api_gateway_name', 'name'), 'parameters', 'data_binary']
        return utils.parse_arg_list(api_gtw_args, cmd_args)     
        
    def parse_s3_args(self, cmd_args):
        s3_args = ['deployment_bucket', 
                   'input_bucket', 
                   'input_folder', 
                   'output_bucket', 
                   'output_folder', 
                   ('bucket', 'input_bucket'), 
                   ('bucket_folder', 'input_folder')]
        return utils.parse_arg_list(s3_args, cmd_args)        
        