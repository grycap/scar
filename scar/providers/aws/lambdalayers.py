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

import io
import shutil
import zipfile
from typing import Dict, List
from tabulate import tabulate
import scar.http.request as request
import scar.logger as logger
from scar.parser.cfgfile import ConfigFileParser
from scar.utils import DataTypesUtils, FileUtils, GitHubUtils


class Layer():

    def __init__(self, lambda_client):
        self.client = lambda_client

    def create(self, **kwargs: Dict) -> Dict:
        """Creates a new layer with the arguments passed."""
        return self.client.publish_layer_version(**kwargs)

    @staticmethod
    def _find(layers_info: Dict, layer_name: str) -> Dict:
        """Returns the layer information that matches the layer name passed."""
        for layer in layers_info.get('Layers', []):
            if layer.get('LayerName', '') == layer_name:
                return layer
        return {}

    def get_info(self, layer_name: str, next_token: str=None):
        """Searches for the layer_name information."""
        all_layers_info = self.client.list_layers(Marker=next_token)
        layer_info = Layer._find(all_layers_info, layer_name)
        if not layer_info and 'NextMarker' in all_layers_info:
            layer_info = self.get_info(layer_name, next_token=all_layers_info['NextMarker'])
        return layer_info

    def exists(self, layer_name: str) -> bool:
        """Checks layer name for existence."""
        if self.get_info(layer_name):
            return True
        return False

    def delete(self, **kwargs: Dict) -> Dict:
        """Deletes a layer."""
        layer_args = {'LayerName' : kwargs['name']}
        if kwargs['version']:
            layer_args['VersionNumber'] = int(kwargs['version'])
        else:
            layer_args['VersionNumber'] = self.get_latest_version(kwargs['name'])
        return self.client.delete_layer_version(**layer_args)

    def get_latest_version(self, layer_name: str) -> str:
        """Returns the latest matching version of the layer with 'layer_name'."""
        layer = self.get_info(layer_name)
        return layer['LatestMatchingVersion']['Version'] if layer else ""


class LambdaLayers():

    _SUPERVISOR_LAYER_NAME = 'faas-supervisor'

    @DataTypesUtils.lazy_property
    def layer(self):
        layer = Layer(self.client)
        return layer

    def __init__(self, lambda_client: Dict):
        self.client = lambda_client
        self.supervisor_version = ConfigFileParser().get_supervisor_version()
        self.supervisor_zip_url = GitHubUtils.get_source_code_url('grycap',
                                                                  'faas-supervisor',
                                                                  self.supervisor_version)
        self.layer_zip_path = FileUtils.join_paths(FileUtils.get_tmp_dir(),
                                                   f"{self._SUPERVISOR_LAYER_NAME}.zip")

    def _create_tmp_folders(self) -> None:
        self.tmp_zip_folder = FileUtils.create_tmp_dir()
        self.tmp_zip_path = self.tmp_zip_folder.name
        self.layer_code_folder = FileUtils.create_tmp_dir()
        self.layer_code_path = self.layer_code_folder.name

    def _download_supervisor(self) -> str:
        """Returns the folder name to remove from the """
        supervisor_zip = request.get_file(self.supervisor_zip_url)
        with zipfile.ZipFile(io.BytesIO(supervisor_zip)) as thezip:
            for file in thezip.namelist():
                # Remove the parent folder path
                parent_folder, file_name = file.split("/", 1)
                if file_name.startswith("extra") or file_name.startswith("faassupervisor"):
                    thezip.extract(file, self.tmp_zip_path)
        return parent_folder

    def _copy_supervisor_files(self, parent_folder: str) -> None:
        supervisor_path = FileUtils.join_paths(self.tmp_zip_path, parent_folder, 'faassupervisor')
        shutil.move(supervisor_path, FileUtils.join_paths(self.layer_code_path, 'python', 'faassupervisor'))

    def _copy_extra_files(self, parent_folder: str) -> None:
        extra_folder_path = FileUtils.join_paths(self.tmp_zip_path, parent_folder, 'extra')
        files = FileUtils.get_all_files_in_directory(extra_folder_path)
        for file_path in files:
            FileUtils.unzip_folder(file_path, self.layer_code_path)

    def _create_layer_zip(self) -> None:
        FileUtils.zip_folder(self.layer_zip_path, self.layer_code_path)

    def _get_supervisor_layer_props(self) -> Dict:
        return {'LayerName' : self._SUPERVISOR_LAYER_NAME,
                'Description' : 'FaaS supervisor that allows to run containers in rootless environments',
                'Content' : {'ZipFile': FileUtils.read_file(self.layer_zip_path, mode="rb")},
                'LicenseInfo' : 'Apache 2.0'}

    def is_supervisor_layer_created(self) -> bool:
        return self.layer.exists(self._SUPERVISOR_LAYER_NAME)

    def _create_layer(self) -> None:
        self._create_tmp_folders()
        parent_folder = self._download_supervisor()
        self._copy_supervisor_files(parent_folder)
        self._copy_extra_files(parent_folder)
        self._create_layer_zip()
        supervisor_layer_props = self._get_supervisor_layer_props()
        self.layer.create(**supervisor_layer_props)
        FileUtils.delete_file(self.layer_zip_path)

    def create_supervisor_layer(self) -> None:
        logger.info("Creating faas-supervisor layer")
        self._create_layer()
        logger.info("Faas-supervisor layer created")

    def update_supervisor_layer(self) -> None:
        logger.info("Updating faas-supervisor layer")
        self._create_layer()
        logger.info("Faas-supervisor layer updated")

    def get_all_layers_info(self) -> List:
        result = []
        layers_info = self.client.list_layers()
        if 'Layers' in layers_info:
            result.extend(layers_info['Layers'])
        while 'NextMarker' in layers_info:
            layers_info = self.client.list_layers(Marker=layers_info['NextMarker'])
            if 'Layers' in layers_info:
                result.extend(layers_info['Layers'])
        return result

    def print_layers_info(self) -> None:
        """Prints the lambda layers information."""
        layers_info = self.get_all_layers_info()
        headers = ['NAME', 'VERSION', 'ARN', 'RUNTIMES']
        table = []
        for layer in layers_info:
            table.append([layer['LayerName'],
                          layer['LatestMatchingVersion']['Version'],
                          layer['LayerArn'],
                          layer['LatestMatchingVersion'].get('CompatibleRuntimes', '-')])
        print(tabulate(table, headers))

    def get_latest_supervisor_layer_arn(self) -> str:
        layer_info = self.layer.get_info(self._SUPERVISOR_LAYER_NAME)
        return layer_info['LatestMatchingVersion']['LayerVersionArn']
