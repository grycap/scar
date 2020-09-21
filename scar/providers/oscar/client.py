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
"""Module with the class implementing the low-level functions to 
communicate with an OSCAR cluster."""

from typing import Dict, List
import scar.logger as logger
import scar.exceptions as excp
import requests

# Disable InsecureRequestWarning in requests package
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def _get_error_msg(res: requests.Response) -> str:
    error_msg = ''
    if res.text:
        error_msg = res.text
    elif res.status_code == 400:
        error_msg = 'Bad Request'
    elif res.status_code == 401:
        error_msg = 'Invalid Credentials'
    elif res.status_code == 404:
        error_msg = 'The Service doesn\'t exist'
    elif res.status_code == 500:
        error_msg = 'Internal Server Error'
    return error_msg    


class OSCARClient():
    _SERVICES_PATH = '/system/services'

    def __init__(self, credentials_info: Dict, cluster_id: str):
        self.cluster_id = cluster_id
        self.endpoint = credentials_info['endpoint']
        self.auth_user = credentials_info['auth_user']
        self.auth_password = credentials_info['auth_password']
        self.ssl_verify = credentials_info['ssl_verify']
        
    def create_service(self, **kwargs: Dict) -> Dict:
        """Creates a new OSCAR service."""
        logger.debug('Creating OSCAR service.')
        res = requests.post(
            f'{self.endpoint}{self._SERVICES_PATH}',
            auth=(self.auth_user, self.auth_password),
            verify=self.ssl_verify,
            json=kwargs
        )
        # Raise a ServiceCreationError if the return code is not 201
        if res.status_code != 201:
            raise excp.ServiceCreationError(service_name=kwargs['name'], error_msg=_get_error_msg(res))

    def delete_service(self, service_name: str) -> None:
        """Deletes an OSCAR service."""
        logger.debug('Deleting OSCAR service.')
        res = requests.delete(
            f'{self.endpoint}{self._SERVICES_PATH}/{service_name}',
            auth=(self.auth_user, self.auth_password),
            verify=self.ssl_verify
        )
        # Raise a ServiceDeletionError if the return code is not 204
        if res.status_code != 204:
            raise excp.ServiceDeletionError(service_name=service_name, error_msg=_get_error_msg(res))

    def get_service(self, service_name: str) -> Dict:
        """Get the properties of the specified service."""
        res = requests.get(
            f'{self.endpoint}{self._SERVICES_PATH}/{service_name}',
            auth=(self.auth_user, self.auth_password),
            verify=self.ssl_verify
        )
        # Raise a ServiceNotFoundError if the return code is not 200
        if res.status_code != 200:
            raise excp.ServiceNotFoundError(service_name=service_name, error_msg=_get_error_msg(res))
        return res.json()

    def list_services(self) -> List:
        """Get all the services registered in the cluster."""
        res = requests.get(
            f'{self.endpoint}{self._SERVICES_PATH}',
            auth=(self.auth_user, self.auth_password),
            verify=self.ssl_verify
        )
        # Raise a ListServicesError if the return code is not 200
        if res.status_code != 200:
            raise excp.ListServicesError(cluster_id=self.cluster_id, error_msg=_get_error_msg(res))
        return res.json()
