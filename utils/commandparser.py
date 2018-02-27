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
import logging
from . import functionutils as utils

class CommandParser(object):
    
    def __init__(self, scar):
        self.scar = scar
        self.parser = argparse.ArgumentParser(prog="scar",
                                         description="Deploy containers in serverless architectures",
                                         epilog="Run 'scar COMMAND --help' for more information on a command.")
        self.subparsers = self.parser.add_subparsers(title='Commands')    
        self.create_init_parser()
        self.create_run_parser()
        self.create_rm_parser()
        self.create_ls_parser()
        self.create_log_parser()
    
    def create_init_parser(self):
        parser_init = self.subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=self.scar.init)
        # Set the mutually exclusive parameters
        group = parser_init.add_mutually_exclusive_group(required=True)
        group.add_argument("-i", "--image_id", help="Container image id (i.e. centos:7)")
        group.add_argument("-if", "--image_file", help="Container image file (i.e. centos.tar.gz)")
        # Set the optional arguments
        parser_init.add_argument("-d", "--description", help="Lambda function description.")
        parser_init.add_argument("-db", "--deployment_bucket", help="Bucket where the deployment package is going to be uploaded.")
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
        parser_init.add_argument("-ep", "--extra_payload", help="Folder containing files that are going to be added to the payload of the lambda function")
    
    def create_run_parser(self):
        parser_run = self.subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=self.scar.run)
        parser_run.add_argument("name", help="Lambda function name")
        parser_run.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_run.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_run.add_argument("-e", "--environment_variables", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
        parser_run.add_argument("-a", "--async", help="Tell Scar to wait or not for the lambda function return", action="store_true")
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
        parser_log.add_argument("name", help="Lambda function name")
        parser_log.add_argument("-ls", "--log_stream_name", help="Return the output for the log stream specified.")
        parser_log.add_argument("-ri", "--request_id", help="Return the output for the request id specified.")        
    
    def parse_arguments(self):
        try:
            """Command parsing and selection"""
            return self.parser.parse_args()        
        except AttributeError as ae:
            logging.error("Error parsing arguments: %s" % ae)
            print("Incorrect arguments: use scar -h to see the options available")
            utils.finish_failed_execution() 
        