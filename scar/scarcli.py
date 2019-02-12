#! /usr/bin/python

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

import sys
sys.path.append('.')

from scar.cmdtemplate import Commands
from scar.parser.cfgfile import ConfigFileParser
from scar.parser.cli import CommandParser
from scar.parser.yaml import YamlParser
from scar.providers.aws.controller import AWS
import scar.exceptions as excp
import scar.logger as logger
import scar.utils as utils

class ScarCLI(Commands):
    
    def __init__(self):
        self.cloud_provider = AWS()
     
    def init(self):
        self.cloud_provider.init()
    
    def invoke(self):
        self.cloud_provider.invoke()    
    
    def run(self):
        self.cloud_provider.run()
        
    def update(self):
        self.cloud_provider.update()        
    
    def ls(self):
        self.cloud_provider.ls()
    
    def rm(self):
        self.cloud_provider.rm()
    
    def log(self):
        self.cloud_provider.log()
        
    def put(self):
        self.cloud_provider.put()
        
    def get(self):
        self.cloud_provider.get()        
    
    @excp.exception(logger)        
    def parse_arguments(self):
        '''
        Merge the scar.conf parameters, the cmd parameters and the yaml file parameters in a single dictionary.
        
        The precedence of parameters is CMD >> YAML >> SCAR.CONF
        That is, the CMD parameter will override any other configuration, 
        and the YAML parameters will override the SCAR.CONF settings
        '''
        merged_args = ConfigFileParser().get_properties()
        cmd_args = CommandParser(self).parse_arguments()
        if 'conf_file' in cmd_args['scar'] and cmd_args['scar']['conf_file']:
            yaml_args = YamlParser(cmd_args['scar']).parse_arguments()
            merged_args = utils.merge_dicts(yaml_args, merged_args)
        merged_args = utils.merge_dicts(cmd_args, merged_args)
        self.cloud_provider.parse_arguments(**merged_args)
        merged_args['scar']['func']()

def main():
    logger.init_execution_trace()
    try:
        ScarCLI().parse_arguments()
        logger.end_execution_trace()
    except:
        logger.end_execution_trace_with_errors()
        
if __name__ == "__main__":
    main()
    
