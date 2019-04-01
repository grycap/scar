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

import json
import os
import scar.exceptions as excp
import scar.logger as logger
import scar.utils as utils
import shutil

default_cfg = {
    "scar" : {
        "layers": { "faas-supervisor" : {"version_url" : "https://api.github.com/repos/grycap/faas-supervisor/releases/latest",
                                         "zip_url" : "https://github.com/grycap/faas-supervisor/archive/{0}.zip",
                                         "default_version" : "master",
                                         "layer_name" : "faas-supervisor"}
        },
        "udocker_info" : {
            "zip_url" : "https://github.com/grycap/faas-supervisor/raw/master/extra/udocker.zip"
        },
    },
    "aws" : {
        "boto_profile" : "default",
        "region" : "us-east-1",
        "execution_mode": "lambda",        
        "iam" : {"role" : ""},
        "lambda" : {
          "time" : 300,
          "memory" : 512,
          "description" : "Automatically generated lambda function",
          "timeout_threshold" : 10 ,
          "runtime" : "python3.6",
          "max_payload_size" : 52428800,
          "max_s3_payload_size" : 262144000
        },
        "cloudwatch" : { "log_retention_policy_in_days" : 30 },
        "batch" : {
          "state": "ENABLED",
          "type": "MANAGED",
          "security_group_ids": [""],
          "comp_type": "EC2",
          "desired_v_cpus": 0,
          "min_v_cpus": 0,
          "max_v_cpus": 2,
          "subnets": [""],
          "instance_types": ["m3.medium"],
          "supervisor_image": "grycap/scar-batch-io:storage",
        },
    }
}

class ConfigFileParser(object):
    
    config_file_name = "scar.cfg"
    backup_config_file_name = "scar.cfg_old"
    config_folder_name = ".scar"
    config_file_folder = utils.join_paths(os.path.expanduser("~"), config_folder_name)
    config_file_path = utils.join_paths(config_file_folder, config_file_name)
    backup_file_path = utils.join_paths(config_file_folder, backup_config_file_name)

    @excp.exception(logger)
    def __init__(self):
        # Check if the config file exists
        if os.path.isfile(self.config_file_path):
            with open(self.config_file_path) as cfg_file:
                self.cfg_data = json.load(cfg_file)
            if 'region' not in self.cfg_data['aws'] or \
               'boto_profile' not in self.cfg_data['aws'] or \
               'execution_mode' not in self.cfg_data['aws'] or \
               'scar' not in self.cfg_data:
                self._add_missing_attributes()
        else:
            # Create scar config dir
            os.makedirs(self.config_file_folder, exist_ok=True)
            self._create_default_config_file()
            raise excp.ScarConfigFileError(file_path=self.config_file_path)
        
    def _create_default_config_file(self):
        with open(self.config_file_path, mode='w') as cfg_file:
            cfg_file.write(json.dumps(default_cfg, indent=2))        
        
    def get_properties(self):
        return self.cfg_data
    
    def get_faas_supervisor_layer_info(self):
        return self.cfg_data['scar']['layers']['faas-supervisor']
    
    def get_udocker_zip_url(self):
        return self.cfg_data['scar']['udocker_info']['zip_url']

    def _add_missing_attributes(self):
        logger.info("Updating old scar config file '{0}'.\n".format(self.config_file_path))
        shutil.copy(self.config_file_path, self.backup_file_path)
        logger.info("Old scar config file saved in '{0}'.\n".format(self.backup_file_path))       
        self._merge_files(self.cfg_data, default_cfg)
        self._delete_unused_data()
        with open(self.config_file_path, mode='w') as cfg_file:
            cfg_file.write(json.dumps(self.cfg_data, indent=2))
    
    def _merge_files(self, cfg_data, default_data):
        for k, v in default_data.items():
            if k not in cfg_data:
                cfg_data[k] = v
            elif type(cfg_data[k]) is dict:
                self._merge_files(cfg_data[k], default_data[k])
                
    def _delete_unused_data(self):
        if 'region' in self.cfg_data['aws']['lambda']:
            region = self.cfg_data['aws']['lambda'].pop('region', None)
            if region:
                self.cfg_data['aws']['region'] = region
