#! /usr/bin/python

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

from aws.awsmanager import AWSManager
from utils.commandparser import CommandParser
from utils.commandtemplate import Commands
import utils.logger as logger 

class Scar(Commands):
    
    def __init__(self):
        self.cloud_provider = AWSManager()
     
    def init(self):
        self.cloud_provider.init()
    
    def run(self):
        self.cloud_provider.run()
    
    def ls(self):
        self.cloud_provider.ls()
    
    def rm(self):
        self.cloud_provider.rm()
    
    def log(self):
        self.cloud_provider.log()
        
    def parse_command_arguments(self):
        args = CommandParser(self).parse_arguments()
        self.cloud_provider.parse_command_arguments(args)
        args.func()

if __name__ == "__main__":
    logger.init_execution_trace()
    Scar().parse_command_arguments()
    logger.end_execution_trace()  
    
