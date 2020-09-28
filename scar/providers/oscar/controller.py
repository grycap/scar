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
"""Module with class and methods used to manage the OSCAR provider."""

from typing import Dict
from copy import deepcopy
from scar.utils import StrUtils, FileUtils, SupervisorUtils
from scar.providers.oscar.client import OSCARClient
from scar.providers.aws.controller import add_output
import scar.exceptions as excp
import scar.logger as logger
import scar.providers.oscar.response as response_parser


def _get_creation_args(resources_info: Dict, storage_providers: Dict) -> Dict:
    creation_args = {}
    # Clean None values
    for k,v in resources_info.items():
        if v:
            creation_args[k] = v
    # Get the content of 'script'
    creation_args['script'] = FileUtils.read_file(creation_args['script'])
    # Add storage_providers
    creation_args['storage_providers'] = storage_providers
    return creation_args


def _get_credentials_info(resources_info: Dict) -> Dict:
    return {
        'endpoint': resources_info.get('endpoint', ''),
        'auth_user': resources_info.get('auth_user', ''),
        'auth_password': resources_info.get('auth_password', ''),
        'ssl_verify': resources_info.get('ssl_verify', True)
    }

def _are_credentials_defined(credentials_info: Dict) -> bool:
    return (credentials_info['endpoint'] and
            credentials_info['auth_user'] and
            credentials_info['auth_password'])


class OSCAR():

    def __init__(self, func_call: Dict):
        self.raw_args = FileUtils.load_tmp_config_file()
        # Flatten the list of services
        self.oscar_resources = []
        nested_resources = self.raw_args.get('functions', {}).get('oscar', [])
        for resources in nested_resources:
            for cluster_id, resources_info in resources.items():
                if ('name' in resources[cluster_id] and
                        resources[cluster_id]['name']):
                    resources_info['cluster_id'] = cluster_id
                    self.oscar_resources.append(resources_info)
        # Store the storage_providers dict independently
        self.storage_providers = self.raw_args.get('storage_providers', {})
        self.scar_info = self.raw_args.get('scar', {})
        add_output(self.scar_info)
        # Call the user's command
        getattr(self, func_call)()

    @excp.exception(logger)
    def init(self):
        for resources_info in self.oscar_resources:
            resources_info = deepcopy(resources_info)
            self._create_oscar_service(resources_info)
            response_parser.parse_service_creation(resources_info, self.scar_info.get('cli_output'))

    @excp.exception(logger)
    def rm(self):
        for resources_info in self.oscar_resources:
            resources_info = deepcopy(resources_info)
            credentials_info = _get_credentials_info(resources_info)
            OSCARClient(credentials_info, resources_info.get('cluster_id', '')).delete_service(resources_info['name'])
            response_parser.parse_service_deletion(resources_info, self.scar_info.get('cli_output'))

    def _create_oscar_service(self, resources_info: Dict):
        credentials_info = _get_credentials_info(resources_info)
        creation_args = _get_creation_args(resources_info, self.storage_providers)
        OSCARClient(credentials_info, resources_info.get('cluster_id', '')).create_service(**creation_args)

    @excp.exception(logger)
    def ls(self):
        clusters = self.raw_args.get('functions', {}).get('oscar', [{}])[0]
        for cluster_id, resources_info in clusters.items():
            credentials_info = _get_credentials_info(resources_info)
            if _are_credentials_defined(credentials_info):
                oscar_resources = OSCARClient(credentials_info, cluster_id).list_services()
                response_parser.parse_ls_response(oscar_resources,
                                                  credentials_info['endpoint'],
                                                  cluster_id,
                                                  self.scar_info.get('cli_output'))
