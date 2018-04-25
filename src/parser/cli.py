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
        self.create_rm_parser()
        self.create_ls_parser()
        self.create_log_parser()        
    
    def create_init_parser(self):
        parser_init = self.subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=self.scar.init)
        group = parser_init.add_mutually_exclusive_group(required=True)
        group.add_argument("-i", "--image_id", help="Container image id (i.e. centos:7)")
        group.add_argument("-if", "--image_file", help="Container image file (i.e. centos.tar.gz)")
        parser_init.add_argument("-d", "--description", help="Lambda function description.")
        parser_init.add_argument("-db", "--deployment_bucket", help="Bucket where the deployment package is going to be uploaded.")
        parser_init.add_argument("-ob", "--output_bucket", help="Bucket name where the output of the function is saved.")
        parser_init.add_argument("-ol", "--output_lambda", help="Lambda function name where the output will be redirected")
        parser_init.add_argument("-e", "--environment_variables", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_init.add_argument("-n", "--name", help="Lambda function name")
        parser_init.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_init.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_init.add_argument("-tt", "--timeout_threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
        parser_init.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_init.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_init.add_argument("-s", "--script", help="Path to the input file passed to the function")
        parser_init.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
        parser_init.add_argument("-lr", "--lambda_role", help="Lambda role used in the management of the functions")
        parser_init.add_argument("-r", "--recursive", help="Launch a recursive lambda function", action="store_true")
        parser_init.add_argument("-p", "--preheat", help="Preheats the function running it once and downloading the necessary container", action="store_true")
        parser_init.add_argument("-ep", "--extra_payload", help="Folder containing files that are going to be added to the lambda function")
        parser_init.add_argument("-api", "--api_gateway_name", help="API Gateway name created to launch the lambda function")
        
    def create_invoke_parser(self):
        parser_invoke = self.subparsers.add_parser('invoke', help="Call a lambda function using an HTTP request")
        # Set default function
        parser_invoke.set_defaults(func=self.scar.invoke)
        parser_invoke.add_argument("-n", "--name", help="Lambda function name (mandatory).", required=True)
        parser_invoke.add_argument("-X", "--request", help="Specify request command to use (i.e. GET or POST) (default: GET).", default='GET')
        parser_invoke.add_argument("-db", "--data-binary", help="File path of the HTTP data to POST.")
        parser_invoke.add_argument("-a", "--asynchronous", help="Tells Scar to wait or not for the lambda function return.", action="store_true")
        parser_invoke.add_argument("-p", "--parameters", help="In addition to passing the parameters in the URL, you can pass the parameters here (i.e. '{\"key1\": \"value1\", \"key2\": [\"value2\", \"value3\"]}').")  
    
    def create_run_parser(self):
        parser_run = self.subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=self.scar.run)
        parser_run.add_argument("-n", "--name", help="Lambda function name", required=True)
        parser_run.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_run.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_run.add_argument("-e", "--environment_variables", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_run.add_argument("-a", "--asynchronous", help="Tells Scar to wait or not for the lambda function return", action="store_true")
        parser_run.add_argument("-s", "--script", nargs='?', type=argparse.FileType('r'), help="Path to the input file passed to the function")
        parser_run.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_run.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
        parser_run.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
        parser_run.add_argument('cont_args', nargs=argparse.REMAINDER, help="Arguments passed to the container.")
    
    def create_rm_parser(self):
        parser_rm = self.subparsers.add_parser('rm', help="Delete function")
        parser_rm.set_defaults(func=self.scar.rm)
        group = parser_rm.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-a", "--all", help="Delete all lambda functions", action="store_true")
        parser_rm.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_rm.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")  
                    
    def create_ls_parser(self):
        parser_ls = self.subparsers.add_parser('ls', help="List lambda functions")
        parser_ls.set_defaults(func=self.scar.ls)
        parser_ls.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
        parser_ls.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
            
    def create_log_parser(self):
        parser_log = self.subparsers.add_parser('log', help="Show the logs for the lambda function")
        parser_log.set_defaults(func=self.scar.log)
        parser_log.add_argument("-n", "--name", help="Lambda function name", required=True)
        parser_log.add_argument("-ls", "--log_stream_name", help="Return the output for the log stream specified.")
        parser_log.add_argument("-ri", "--request_id", help="Return the output for the request id specified.")        
    
    def put(self):
        pass
    
    def get(self):
        pass        
    
    def parse_arguments(self):
        '''Command parsing and selection'''
        try:
            return self.parser.parse_args()        
        except AttributeError as ae:
            logger.error("Incorrect arguments: use scar -h to see the options available",
                             "Error parsing arguments: %s" % ae)            
            utils.finish_failed_execution() 
        