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
from typing import Dict
import zipfile

import scar.http.request as request
import scar.logger as logger
from scar.utils import DataTypesUtils, FileUtils, GitHubUtils, StrUtils
from tabulate import tabulate


def _create_tmp_folders() -> None:
    tmp_zip_folder = FileUtils.create_tmp_dir()
    layer_code_folder = FileUtils.create_tmp_dir()
    return (tmp_zip_folder.name, layer_code_folder.name)


def _copy_supervisor_files(parent_folder: str, tmp_zip_path: str, layer_code_path: str) -> None:
    supervisor_path = FileUtils.join_paths(tmp_zip_path, parent_folder, 'faassupervisor')
    shutil.move(supervisor_path, FileUtils.join_paths(layer_code_path, 'python', 'faassupervisor'))


def _copy_extra_files(parent_folder: str, tmp_zip_path: str, layer_code_path: str) -> None:
    extra_folder_path = FileUtils.join_paths(tmp_zip_path, parent_folder, 'extra')
    files = FileUtils.get_all_files_in_directory(extra_folder_path)
    for file_path in files:
        FileUtils.unzip_folder(file_path, layer_code_path)


def _create_layer_zip(layer_zip_path: str, layer_code_path: str) -> None:
    FileUtils.zip_folder(layer_zip_path, layer_code_path)


def _download_supervisor(supervisor_version: str, tmp_zip_path: str) -> str:
    """Returns the folder name to remove from the """
    supervisor_zip_url = GitHubUtils.get_source_code_url('grycap', 'faas-supervisor',
                                                         supervisor_version)
    supervisor_zip = request.get_file(supervisor_zip_url)
    with zipfile.ZipFile(io.BytesIO(supervisor_zip)) as thezip:
        for file in thezip.namelist():
            # Remove the parent folder path
            parent_folder, file_name = file.split("/", 1)
            if file_name.startswith("extra") or file_name.startswith("faassupervisor"):
                thezip.extract(file, tmp_zip_path)
    return parent_folder


class Layer():
    """Class used for layer management."""

    def __init__(self, lambda_client) -> None:
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

    def delete(self, **kwargs: Dict) -> Dict:
        """Deletes a layer."""
        layer_args = {'LayerName' : kwargs['name']}
        if 'version' in kwargs:
            layer_args['VersionNumber'] = int(kwargs['version'])
        else:
            version_info = self.get_latest_layer_info(kwargs['name'])
            layer_args['VersionNumber'] = version_info.get('Version', -1)
        return self.lambda_client.delete_layer_version(**layer_args)

    def get_latest_layer_info(self, layer_name: str) -> str:
        """Returns the latest matching version of the layer with 'layer_name'."""
        layer = self._find(layer_name)
        return layer['LatestMatchingVersion'] if layer else {}


class LambdaLayers():
    """"Class used to manage the lambda supervisor layer."""

    _SUPERVISOR_LAYER_NAME = 'faas-supervisor'

    @DataTypesUtils.lazy_property
    def layer(self):
        """Property used to manage the lambda layers."""
        layer = Layer(self.lambda_client)
        return layer

    def __init__(self, lambda_client, supervisor_version: str) -> None:
        self.lambda_client = lambda_client
        self.supervisor_version = supervisor_version

    def _get_supervisor_layer_props(self, layer_zip_path: str) -> Dict:
        return {'LayerName' : self._SUPERVISOR_LAYER_NAME,
                'Description' : self.supervisor_version,
                'Content' : {'ZipFile': FileUtils.read_file(layer_zip_path, mode="rb")},
                'LicenseInfo' : 'Apache 2.0'}

    def _create_layer(self) -> None:
        tmp_zip_path, layer_code_path = _create_tmp_folders()
        layer_zip_path = FileUtils.join_paths(FileUtils.get_tmp_dir(),
                                              f"{self._SUPERVISOR_LAYER_NAME}.zip")
        parent_folder = _download_supervisor(self.supervisor_version, tmp_zip_path)
        _copy_supervisor_files(parent_folder, tmp_zip_path, layer_code_path)
        _copy_extra_files(parent_folder, tmp_zip_path, layer_code_path)
        _create_layer_zip(layer_zip_path, layer_code_path)
        self.layer.create(**self._get_supervisor_layer_props(layer_zip_path))
        FileUtils.delete_file(layer_zip_path)

    def _create_supervisor_layer(self) -> None:
        logger.info("Creating faas-supervisor layer.")
        self._create_layer()
        logger.info("Faas-supervisor layer created.")

    def _update_supervisor_layer(self) -> None:
        logger.info("Updating faas-supervisor layer.")
        self._create_layer()
        logger.info("Faas-supervisor layer updated.")

    def print_layers_info(self) -> None:
        """Prints the lambda layers information."""
        layers_info = self.lambda_client.list_layers()
        headers = ['NAME', 'VERSION', 'ARN', 'RUNTIMES']
        table = []
        for layer in layers_info:
            table.append([layer.get('LayerName', ""),
                          layer.get('LatestMatchingVersion', {}).get('Version', -1),
                          layer.get('LayerArn', ""),
                          layer.get('LatestMatchingVersion', {}).get('CompatibleRuntimes', '-')])
        print(tabulate(table, headers))

    def get_latest_supervisor_layer_arn(self) -> str:
        """Returns the ARN of the latest supervisor layer."""
        layer_info = self.layer.get_latest_layer_info(self._SUPERVISOR_LAYER_NAME)
        return layer_info.get('LayerVersionArn', "")

    def check_faas_supervisor_layer(self):
        """Checks if the supervisor layer exists, if not, creates the layer.
        If the layer exists and it's not updated, updates the layer."""
        # Get the layer information
        layer_info = self.layer.get_latest_layer_info(self._SUPERVISOR_LAYER_NAME)
        # Compare supervisor versions
        if layer_info and 'Description' in layer_info:
            # If the supervisor layer version is lower than the passed version,
            # we must update the layer
            if StrUtils.compare_versions(layer_info.get('Description', ''),
                                         self.supervisor_version) < 0:
                self._update_supervisor_layer()
            else:
                logger.info("Using existent 'faas-supervisor' layer")
        else:
            # Layer not found, we have to create it
            self._create_supervisor_layer()
