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
"""Module with methods and classes to manage the Lambda layers."""
import shutil
from typing import Dict, List
import zipfile
import scar.logger as logger
from scar.utils import FileUtils
from scar.providers.aws.clients.lambdafunction import LambdaClient


class Layer():
    """Class used for layer management."""

    def __init__(self, lambda_client: LambdaClient) -> None:
        self.lambda_client = lambda_client

    def _find(self, layer_name: str) -> Dict:
        """Returns the layer information that matches the layer name passed."""
        for layer in self.lambda_client.list_layers():
            if layer.get('LayerName', '') == layer_name:
                return layer
        return {}

    def create(self, **kwargs: Dict) -> Dict:
        """Creates a new layer with the arguments passed."""
        return self.lambda_client.publish_layer_version(**kwargs)

    def exists(self, layer_name: str) -> bool:
        """Checks layer name for existence."""
        if self._find(layer_name):
            return True
        return False

    def list_versions(self, layer_name: str) -> List:
        return self.lambda_client.list_layer_versions(layer_name)

    def delete(self, **kwargs: Dict) -> Dict:
        """Deletes a layer."""
        layer_args = {'LayerName': kwargs['name']}
        if 'version' in kwargs:
            layer_args['VersionNumber'] = int(kwargs['version'])
        else:
            version_info = self.get_latest_layer_info(kwargs['name'])
            layer_args['VersionNumber'] = version_info.get('Version', -1)
        return self.lambda_client.delete_layer_version(**layer_args)

    def get_latest_layer_info(self, layer_name: str) -> Dict:
        """Returns the latest matching version of the layer with 'layer_name'."""
        layer = self._find(layer_name)
        return layer['LatestMatchingVersion'] if layer else {}


class LambdaLayers():
    """"Class used to manage the lambda supervisor layer."""

    # To avoid circular inheritance we need to receive the LambdaClient
    def __init__(self, resources_info: Dict, lambda_client: LambdaClient, supervisor_zip_path: str):
        self.resources_info = resources_info
        self.supervisor_zip_path = supervisor_zip_path
        self.layer_name = resources_info.get('lambda').get('supervisor').get('layer_name')
        self.supervisor_version = resources_info.get('lambda').get('supervisor').get('version')
        self.layer = Layer(lambda_client)

    def _get_supervisor_layer_props(self, layer_zip_path: str) -> Dict:
        return {'LayerName': self.layer_name,
                'Description': self.supervisor_version,
                'Content': {'ZipFile': FileUtils.read_file(layer_zip_path, mode="rb")},
                'CompatibleRuntimes': ['python3.8', 'python3.7'],
                'LicenseInfo': self.resources_info.get('lambda').get('supervisor').get('license_info')}

    def _create_layer(self) -> str:
        # Create tmp folders
        tmp_path = FileUtils.create_tmp_dir()
        layer_code_path = FileUtils.create_tmp_dir()
        # Extract 'extra' and 'faassupervisor' from supervisor_zip_path
        with zipfile.ZipFile(self.supervisor_zip_path) as thezip:
            for file in thezip.namelist():
                # Remove the parent folder path
                parent_folder, file_name = file.split('/', 1)
                if file_name.startswith('extra') or file_name.startswith('faassupervisor'):
                    thezip.extract(file, tmp_path.name)
        # Extract content of 'extra' files in layer_code_path
        extra_folder_path = FileUtils.join_paths(tmp_path.name, parent_folder, 'extra')
        files = FileUtils.get_all_files_in_directory(extra_folder_path)
        for file_path in files:
            FileUtils.unzip_folder(file_path, layer_code_path.name)
        # Copy 'faassupervisor' to layer_code_path
        supervisor_folder_path = FileUtils.join_paths(tmp_path.name, parent_folder, 'faassupervisor')
        shutil.move(supervisor_folder_path, FileUtils.join_paths(layer_code_path.name, 'python', 'faassupervisor'))
        # Create layer zip with content of layer_code_path
        layer_zip_path = FileUtils.join_paths(tmp_path.name, f'{self.layer_name}.zip')
        FileUtils.zip_folder(layer_zip_path, layer_code_path.name)
        # Register the layer
        props = self._get_supervisor_layer_props(layer_zip_path)
        response = self.layer.create(**props)
        return response['LayerVersionArn']

    def _is_supervisor_created(self) -> bool:
        return self.layer.exists(self.layer_name)

    def _is_supervisor_version_created(self) -> str:
        versions = self.layer.list_versions(self.layer_name)
        for version in versions:
            if 'Description' in version:
                if version['Description'] == self.supervisor_version:
                    return version['LayerVersionArn']
        return ''

    def get_supervisor_layer_arn(self) -> str:
        """Returns the ARN of the specified supervisor layer version.
        If the layer or version doesn't exists, creates the layer."""
        if self._is_supervisor_created():
            is_created = self._is_supervisor_version_created()
            if is_created != '':
                logger.info(f'Using existent \'{self.layer_name}\' layer.')
                return is_created
        logger.info((f'Creating lambda layer with \'{self.layer_name}\''
                     f' version \'{self.supervisor_version}\'.'))
        return self._create_layer()
