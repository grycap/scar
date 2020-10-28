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

from scar.parser.cfgfile import ConfigFileParser
from scar.parser.cli import CommandParser
from scar.providers.aws.controller import AWS
from scar.providers.oscar.controller import OSCAR
from scar.utils import FileUtils
import scar.parser.fdl as fdl
import scar.exceptions as excp
import scar.logger as logger


@excp.exception(logger)
def parse_arguments():
    """
    Merge the scar.conf parameters, the cmd parameters and the yaml
    file parameters in a single dictionary.

    The precedence of parameters is CMD >> YAML >> SCAR.CONF
    That is, the CMD parameter will override any other configuration,
    and the YAML parameters will override the SCAR.CONF settings
    """
    config_args = ConfigFileParser().get_properties()
    func_call, cmd_args = CommandParser().parse_arguments()
    if 'conf_file' in cmd_args['scar'] and cmd_args['scar']['conf_file']:
        yaml_args = FileUtils.load_yaml(cmd_args['scar']['conf_file'])
        # YAML >> SCAR.CONF
        merged_args = fdl.merge_conf(config_args, yaml_args)
        merged_args = fdl.merge_cmd_yaml(cmd_args, merged_args)
    else:
        # CMD >> SCAR.CONF
        merged_args = fdl.merge_conf(config_args, cmd_args)
    #self.cloud_provider.parse_arguments(merged_args)
    FileUtils.create_tmp_config_file(merged_args, ConfigFileParser())
    return func_call

def main():
    logger.init_execution_trace()
    try:
        func_call = parse_arguments()
        # Default provider
        # If more providers, analyze the arguments and build the required one
        AWS(func_call)
        # Build the OSCAR controller only with 'init', 'rm' and 'ls' commands
        if func_call in ['init', 'rm', 'ls']:
            OSCAR(func_call)
        logger.end_execution_trace()
    except Exception as excp:
        print(excp)
        logger.exception(excp)
        logger.end_execution_trace_with_errors()


if __name__ == "__main__":
    main()
