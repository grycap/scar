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

import os
import src.logger as logger
import shutil
import json

config_file_folder = os.path.expanduser("~") + "/.scar"
config_file_name = "scar.cfg"
config_file_path = config_file_folder + '/' + config_file_name
default_file_path = os.path.dirname(os.path.realpath(__file__))

class ConfigFile(object):

    def __init__(self):
        # Check if the config file exists
        if os.path.isfile(config_file_path):
            with open(config_file_path) as cfg_file:
                self.__setattr__("cfg_data", json.load(cfg_file))  
        else:
            # Create scar config dir
            os.makedirs(config_file_folder, exist_ok=True)
            self.create_default_config_file()
        
    def create_default_config_file(self):
        shutil.copy(default_file_path + "/default_config_file.json", config_file_path)
        message = "Config file '%s' created.\n" % config_file_path
        message += "Please, set a valid iam role in the file field 'role' before the first execution."
        logger.warning(message)
        
    def get_aws_props(self):
        return self.cfg_data['aws']
        
        
        