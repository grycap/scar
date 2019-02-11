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
import scar.utils as utils
import scar.http.request as request
import zipfile
import scar.logger as logger
import json
import io
import shutil

class LambdaLayers():

    aws_path = os.path.dirname(os.path.abspath(__file__))
    supervisor_layer_name = "faas-supervisor"
    supervisor_zip_path = utils.join_paths(aws_path, "cloud", "layer", "supervisor.zip")
    udocker_zip_path = utils.join_paths(aws_path, "cloud", "layer", "udocker.zip")
    supervisor_version_url = 'https://api.github.com/repos/grycap/faas-supervisor/releases/latest'
    supervisor_zip_url = 'https://github.com/grycap/faas-supervisor/archive/{0}.zip'
    
    def __init__(self, lambda_client):
        self.lambda_client = lambda_client
        self.layers_info = self.get_lambda_layers_info()
        
    def get_lambda_layers_info(self):
        return self.lambda_client.list_layers()['Layers']        
        
    def create_tmp_folders(self):
        self.tmp_zip_folder = utils.create_tmp_dir()
        self.tmp_zip_path = self.tmp_zip_folder.name
        self.layer_code_folder = utils.create_tmp_dir()
        self.layer_code_path = self.layer_code_folder.name

    def get_supervisor_version(self):
        j = json.loads(request.invoke_http_endpoint(self.supervisor_version_url).text)
        return j['tag_name']        

    def download_supervisor(self):
#         supervisor_version = self.get_supervisor_version()
        supervisor_version = 'master'
        self.version_path = 'faas-supervisor-{0}'.format(supervisor_version)
        supervisor_zip = request.get_file(self.supervisor_zip_url.format(supervisor_version))
        with zipfile.ZipFile(io.BytesIO(supervisor_zip)) as thezip:
            for file in thezip.namelist():
                if file.startswith('{}/extra'.format(self.version_path)) or \
                   file.startswith('{}/faassupervisor'.format(self.version_path)):
                    thezip.extract(file, self.tmp_zip_path)

    def get_layer_info(self, layer_name):
        for layer in self.layers_info:
            if layer['LayerName'] == layer_name:
                return layer

    def is_layer_created(self, layer_name):
        if self.get_layer_info(layer_name):
            return True
        return False
    
    def is_supervisor_layer_created(self):
        return self.is_layer_created(self.supervisor_layer_name)
    
    def create_layer(self, **layer_properties):
        return self.lambda_client.publish_layer_version(**layer_properties)    
    
    def copy_supervisor_files(self):
        supervisor_path = utils.join_paths(self.tmp_zip_path, self.version_path, 'faassupervisor')
        shutil.move(supervisor_path, utils.join_paths(self.layer_code_path, 'python', 'faassupervisor'))
        
    def copy_udocker_files(self):
        utils.unzip_folder(utils.join_paths(self.tmp_zip_path, self.version_path, 'extra', 'udocker.zip'), self.layer_code_path)
            
    def create_zip(self):
        self.layer_zip_path = utils.join_paths(utils.get_tmp_dir(), 'faas-supervisor.zip')
        utils.zip_folder(self.layer_zip_path, self.layer_code_path)
    
    def create_supervisor_layer(self):
        logger.info("Creating faas-supervisor layer")
        self.create_tmp_folders()
        self.download_supervisor()        
        self.copy_supervisor_files()
        self.copy_udocker_files()
        self.create_zip()
        supervisor_layer_props = self.get_supervisor_layer_props()
        self.supervisor_layer_info = self.create_layer(**supervisor_layer_props)
        logger.info("Faas-supervisor layer created")
    
    def get_supervisor_layer_props(self):
        return {'LayerName' : self.supervisor_layer_name,
                'Description' : 'FaaS supervisor that allows to run containers in rootless environments',
                'Content' : { 'ZipFile': utils.read_file(self.layer_zip_path, mode="rb") },
                'LicenseInfo' : 'Apache 2.0'}      
        
    def get_layers_arn(self):
        layers = []
        if not hasattr(self, "supervisor_layer_info"):
            self.supervisor_layer_info = self.get_layer_info(self.supervisor_layer_name)
            layers.append(self.supervisor_layer_info['LatestMatchingVersion']['LayerVersionArn'])
        else:
            layers.append(self.supervisor_layer_info['LayerVersionArn'])
        return layers
