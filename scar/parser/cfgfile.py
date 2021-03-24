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
import os
from scar.exceptions import exception, ScarConfigFileError
import scar.logger as logger
from scar.utils import FileUtils, SysUtils, StrUtils

_DEFAULT_CFG = {
    "scar": {
        "config_version": "1.1.0"
    },
    "oscar": {
        "my_oscar": {
            # Cluster credentials
            "endpoint": "",
            "auth_user": "",
            "auth_password": "",
            "ssl_verify": True,
            # Default service parameters
            # Memory limit for the service following the kubernetes format
            # https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/#meaning-of-memory
            "memory": "256Mi",
            # CPU limit for the service following the kubernetes format
	        # https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/#meaning-of-cpu
            "cpu": "0.2",
            "log_level": "INFO",
        }
    },
    "aws": {
        "iam": {"boto_profile": "default",
                "role": ""},
        "lambda": {
            "boto_profile": "default",
            "region": "us-east-1",
            "execution_mode": "lambda",
            "timeout": 300,
            "memory": 512,
            "description": "Automatically generated lambda function",
            "runtime": "python3.7",
            "layers": [],
            "invocation_type": "RequestResponse",
            "asynchronous": False,
            "log_type": "Tail",
            "log_level": "INFO",
            "environment": {
                "Variables": {
                    "UDOCKER_BIN" : "/opt/udocker/bin/",
                    "UDOCKER_LIB" : "/opt/udocker/lib/",
                    "UDOCKER_DIR" : "/tmp/shared/udocker",
                    "UDOCKER_EXEC": "/opt/udocker/udocker.py"}},
            "deployment": {
                "max_payload_size": 52428800,
                "max_s3_payload_size": 262144000           
            },
            "container": {
                "environment" : {
                    "Variables" : {}},
                "timeout_threshold": 10
            },
            # Must be a Github tag or "latest"
            "supervisor": {
                "version": "latest",
                'layer_name' : "faas-supervisor",
                'license_info' : 'Apache 2.0'                
            }
        },
        "s3": {
            "boto_profile": "default",
            "region": "us-east-1",            
            "event" : {
                "Records": [{
                    "eventSource": "aws:s3",
                    "s3" : {
                        "bucket" : {
                            "name": "{bucket_name}",
                            "arn": "arn:aws:s3:::{bucket_name}"
                        },
                        "object" : {
                            "key": "{file_key}"
                        }
                    }
                }]
            }
        },
        "api_gateway": {
            "boto_profile": "default",
            "region": "us-east-1",            
            "endpoint": "https://{api_id}.execute-api.{api_region}.amazonaws.com/{stage_name}/launch",
            'request_parameters': {"integration.request.header.X-Amz-Invocation-Type":
                                   "method.request.header.X-Amz-Invocation-Type"},
            # ANY, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
            'http_method': "ANY",
            "method" : {
                # NONE, AWS_IAM, CUSTOM, COGNITO_USER_POOLS
                'authorizationType': "NONE",
                'requestParameters': {'method.request.header.X-Amz-Invocation-Type' : False},
            },
            "integration": {
                # 'HTTP'|'AWS'|'MOCK'|'HTTP_PROXY'|'AWS_PROXY'
                'type': "AWS_PROXY",
                'integrationHttpMethod' : "POST",
                'uri' : "arn:aws:apigateway:{api_region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{lambda_region}:{account_id}:function:{function_name}/invocations",
                'requestParameters' : {"integration.request.header.X-Amz-Invocation-Type":
                                       "method.request.header.X-Amz-Invocation-Type"}            
            },
            'path_part': "{proxy+}",
            'stage_name': "scar",
            # Used to add invocation permissions to lambda
            'service_id': 'apigateway.amazonaws.com',
            'source_arn_testing': 'arn:aws:execute-api:{api_region}:{account_id}:{api_id}/*',
            'source_arn_invocation': 'arn:aws:execute-api:{api_region}:{account_id}:{api_id}/{stage_name}/ANY'
        },
        "cloudwatch": {
            "boto_profile": "default",
            "region": "us-east-1",
            "log_retention_policy_in_days": 30
        },
        "batch": {
            "multi_node_parallel": {
                "enabled": False,
                "number_nodes": 10,
                "main_node_index": 0
            },
            "boto_profile": "default",
            "region": "us-east-1",
            "vcpus": 1,
            "memory": 1024,
            "enable_gpu": False,
            "state": "ENABLED",
            "type": "MANAGED",
            "environment" : {
                "Variables" : {}},
            "compute_resources": {
                "security_group_ids": [],
                "type": "EC2",
                "desired_v_cpus": 0,
                "min_v_cpus": 0,
                "max_v_cpus": 2,
                "subnets": [],
                "instance_types": ["m3.medium"],
                "launch_template_name": "faas-supervisor",
                "instance_role": "arn:aws:iam::{account_id}:instance-profile/ecsInstanceRole"
            },
            "service_role": "arn:aws:iam::{account_id}:role/service-role/AWSBatchServiceRole"            
        }
    }
}


class ConfigFileParser():
    """Class to manage the SCAR configuration file creation, update and load."""

    _CONFIG_FOLDER_PATH_ENV_VAR = 'SCAR_CONFIG_FOLDER'
    _CONFIG_FOLDER_PATH = ".scar"
    _CONFIG_FILE_PATH = "scar.cfg"
    _CONFIG_FILE_NAME_BCK = "scar.cfg_old"
    _CONFIG_FILE_NAME_TMP_YAML = "scar_tmp.yaml"

    # Set default config folder path
    config_file_folder = FileUtils.join_paths(SysUtils.get_user_home_path(), _CONFIG_FOLDER_PATH)

    # Check if config folder env var is set, and use it for config paths
    if _CONFIG_FOLDER_PATH_ENV_VAR in os.environ:
        config_file_folder = os.getenv(_CONFIG_FOLDER_PATH_ENV_VAR)

    # Set config file paths
    config_file_path = FileUtils.join_paths(config_file_folder, _CONFIG_FILE_PATH)
    backup_file_path = FileUtils.join_paths(config_file_folder, _CONFIG_FILE_NAME_BCK)
    tmp_yaml_file_path = FileUtils.join_paths(config_file_folder, _CONFIG_FILE_NAME_TMP_YAML)

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
        return StrUtils.compare_versions(self.cfg_data.get('scar', {}).get("config_version", ""),
                                         _DEFAULT_CFG['scar']["config_version"]) >= 0

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
