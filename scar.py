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

from src.providers.aws.controller import AWS
from src.parser.cli import CommandParser
from src.cmdtemplate import Commands
import src.logger as logger 

class Scar(Commands):
    
    def __init__(self):
        self.cloud_provider = AWS()
     
    def init(self):
        self.cloud_provider.init()
    
    def invoke(self):
        self.cloud_provider.invoke()    
    
    def run(self):
        self.cloud_provider.run()
    
    def ls(self):
        self.cloud_provider.ls()
    
    def rm(self):
        self.cloud_provider.rm()
    
    def log(self):
        self.cloud_provider.log()
        
    def put(self):
        self.cloud_provider.put()        
        
    def parse_command_arguments(self):
        args = CommandParser(self).parse_arguments()
        if hasattr(args, 'func'):
            self.cloud_provider.parse_command_arguments(args)
            args.func()
        else:
            logger.error("Incorrect arguments: use scar -h to see the options available")

if __name__ == "__main__":
    logger.init_execution_trace()
    Scar().parse_command_arguments()
    logger.end_execution_trace()  
    
