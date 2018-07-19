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
import shutil
import json
import src.utils as utils
import src.exceptions as excp
import src.logger as logger

class ConfigFileParser(object):
    
    config_file_name = "scar.cfg"
    backup_config_file_name = "scar.cfg_old"
    config_folder_name = ".scar"
    default_file_name = "default_config_file.json"
    config_file_folder = utils.join_paths(os.path.expanduser("~"), config_folder_name)
    config_file_path = utils.join_paths(config_file_folder, config_file_name)
    backup_file_path = utils.join_paths(config_file_folder, backup_config_file_name)
    default_file_path = utils.join_paths(os.path.dirname(os.path.realpath(__file__)), default_file_name)


    @excp.exception(logger)
    def __init__(self):
        # Check if the config file exists
        if os.path.isfile(self.config_file_path):
            with open(self.config_file_path) as cfg_file:
                self.__setattr__("cfg_data", json.load(cfg_file))
            if 'region' not in self.cfg_data['aws'] or 'boto_profile' not in self.cfg_data['aws']:
                self.add_missing_attributes()
        else:
            # Create scar config dir
            os.makedirs(self.config_file_folder, exist_ok=True)
            self.create_default_config_file()
            raise excp.ScarConfigFileError(file_path=self.config_file_path)
        
    def create_default_config_file(self):
        shutil.copy(self.default_file_path, self.config_file_path)
        
    def get_properties(self):
        return self.cfg_data
        
    def add_missing_attributes(self):
        print("Updating old scar config file '{0}'.\n".format(self.config_file_path))
        shutil.copy(self.config_file_path, self.backup_file_path)
        print("Old scar config file saved in '{0}'.\n".format(self.backup_file_path))       
        with open(self.default_file_path) as default_file:
            default_data = json.load(default_file)
            self.merge_files(self.cfg_data, default_data)
        self.delete_unused_data()
        with open(self.config_file_path, mode='w') as cfg_file:
            cfg_file.write(json.dumps(self.cfg_data, indent=2))
    
    def merge_files(self, cfg_data, default_data):
        for k, v in default_data.items():
            if k not in cfg_data:
                cfg_data[k] = v
            elif type(cfg_data[k]) is dict:
                self.merge_files(cfg_data[k], default_data[k])
                
    def delete_unused_data(self):
        if 'region' in self.cfg_data['aws']['lambda']:
            region = self.cfg_data['aws']['lambda'].pop('region', None)
            if region:
                self.cfg_data['aws']['region'] = region                             
            
