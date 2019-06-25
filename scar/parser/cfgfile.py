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
"""Module with methods and classes in charge
of managing the SCAR configuration file."""

import json
from packaging import version
from scar.exceptions import exception, ScarConfigFileError
import scar.logger as logger
from scar.utils import FileUtils, SysUtils

_DEFAULT_CFG = {
    "scar": {
        # Must be a tag or "latest"
        "supervisor_version": "latest",
        "config_version": "1.0.0"
    },
    "aws": {
        "boto_profile": "default",
        "region": "us-east-1",
        "execution_mode": "lambda",
        "iam": {"role": ""},
        "lambda": {
            "time": 300,
            "memory": 512,
            "description": "Automatically generated lambda function",
            "timeout_threshold": 10,
            "runtime": "python3.6",
            "max_payload_size": 52428800,
            "max_s3_payload_size": 262144000,
            "layers": []
        },
        "cloudwatch": {"log_retention_policy_in_days": 30},
        "batch": {
            "vcpus": 1,
            "memory": 1024,
            "enable_gpu": False,
            "compute_resources": {
                "state": "ENABLED",
                "type": "MANAGED",
                "security_group_ids": [],
                "comp_type": "EC2",
                "desired_v_cpus": 0,
                "min_v_cpus": 0,
                "max_v_cpus": 2,
                "subnets": [],
                "instance_types": ["m3.medium"]
            }
        }
    }
}


class ConfigFileParser():
    """Class to manage the SCAR configuration file creation, update and load."""

    _CONFIG_FOLDER_PATH = ".scar"
    _CONFIG_FILE_PATH = "scar.cfg"
    _CONFIG_FILE_NAME_BCK = "scar.cfg_old"
    config_file_folder = FileUtils.join_paths(SysUtils.get_user_home_path(), _CONFIG_FOLDER_PATH)
    config_file_path = FileUtils.join_paths(config_file_folder, _CONFIG_FILE_PATH)
    backup_file_path = FileUtils.join_paths(config_file_folder, _CONFIG_FILE_NAME_BCK)

    @exception(logger)
    def __init__(self):
        # Check if the config file exists
        if FileUtils.is_file(self.config_file_path):
            with open(self.config_file_path) as cfg_file:
                self.cfg_data = json.load(cfg_file)
            if not self._is_config_file_updated():
                self._update_config_file()
        else:
            self._create_scar_config_folder_and_file()

    def _is_config_file_updated(self):
        if 'config_version' not in self.cfg_data['scar']:
            return False
        user_cfg_file_ver = version.parse(self.cfg_data['scar']["config_version"])
        def_cfg_file_ver = version.parse(_DEFAULT_CFG['scar']["config_version"])
        return user_cfg_file_ver >= def_cfg_file_ver

    def get_properties(self):
        """Returns the configuration data of the configuration file."""
        return self.cfg_data

    def get_udocker_zip_url(self):
        """Returns the url where the udocker zip is stored."""
        return self.cfg_data['scar']['udocker_info']['zip_url']

    def _create_scar_config_folder_and_file(self):
        FileUtils.create_folder(self.config_file_folder)
        self._create_new_config_file()
        raise ScarConfigFileError(file_path=self.config_file_path)

    def _create_new_config_file(self):
        FileUtils.create_file_with_content(self.config_file_path,
                                           json.dumps(_DEFAULT_CFG, indent=2))

    def _update_config_file(self):
        logger.info(("SCAR configuration file deprecated.\n"
                     "Updating your SCAR configuration file."))
        FileUtils.copy_file(self.config_file_path, self.backup_file_path)
        logger.info(f"Old configuration file saved in '{self.backup_file_path}'.")
        self._create_new_config_file()
        logger.info((f"New configuration file saved in '{self.config_file_path}'.\n"
                     "Please fill your new configuration file with your account information."))
        SysUtils.finish_scar_execution()

#         self._merge_files(self.cfg_data, _DEFAULT_CFG)
#         self._delete_unused_data()
#         with open(self.config_file_path, mode='w') as cfg_file:
#             cfg_file.write(json.dumps(self.cfg_data, indent=2))

#     def _add_missing_attributes(self):
#         logger.info("Updating old scar config file '{0}'.\n".format(self.config_file_path))
#         FileUtils.copy_file(self.config_file_path, self.backup_file_path)
#         logger.info("Old scar config file saved in '{0}'.\n".format(self.backup_file_path))
#         self._merge_files(self.cfg_data, _DEFAULT_CFG)
#         self._delete_unused_data()
#         with open(self.config_file_path, mode='w') as cfg_file:
#             cfg_file.write(json.dumps(self.cfg_data, indent=2))
#
#     def _merge_files(self, cfg_data, default_data):
#         for key, val in default_data.items():
#             if key not in cfg_data:
#                 cfg_data[key] = val
#             elif isinstance(cfg_data[key], dict):
#                 self._merge_files(cfg_data[key], default_data[key])
#
#     def _delete_unused_data(self):
#         if 'region' in self.cfg_data['aws']['lambda']:
#             region = self.cfg_data['aws']['lambda'].pop('region', None)
#             if region:
#                 self.cfg_data['aws']['region'] = region
