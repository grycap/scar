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

from scar.parser.cfgfile import ConfigFileParser
import io
import json
import scar.http.request as request
import scar.logger as logger
import scar.utils as utils
import shutil
import zipfile
from tabulate import tabulate

class Layer():
    
    def __init__(self, lambda_client):
        self.client = lambda_client

    def create(self, **kwargs):
        return self.client.publish_layer_version(**kwargs)
    
    def _find(self, layers_info, layer_name):
        if 'Layers' in layers_info:
            for layer in layers_info['Layers']:
                if layer['LayerName'] == layer_name:
                    return layer        
    
    def get_info(self, layer_name):
        layers_info = self.client.list_layers()
        # Look for the layer in the first batch
        layer = self._find(layers_info, layer_name)
        if layer:
            return layer         
        while 'NextMarker' in layers_info:
            layers_info = self.client.list_layers(Marker=layers_info['NextMarker'])
            layer = self._find(layers_info, layer_name)
            if layer:
                return layer                  
                    
    def exists(self, layer_name):
        return self.get_info(layer_name) != None
        
    def delete(self, **kwargs):
        layer_args = {'LayerName' : kwargs['name']}
        layer_args['VersionNumber'] = int(kwargs['version']) if kwargs['version'] else self.get_latest_version(kwargs['name'])
        return self.client.delete_layer_version(**layer_args)
    
    def get_latest_version(self, layer_name):
        layers = self.get_layers_info()
        for layer in layers['Layers']:
            if layer['LayerName'] == layer_name:
                return layer['LatestMatchingVersion']['Version']
            
class ScarProperties(dict):
    def __init__(self, *args, **kwargs):
        super(ScarProperties, self).__init__(*args, **kwargs)
        self.__dict__ = self

class LambdaLayers():

    @utils.lazy_property
    def layer(self):
        layer = Layer(self.client)
        return layer    
    
    def __init__(self, lambda_client):
        '''
        Default scar's configuration file structure:
        {
            "scar" : {
                "layers": { "faas-supervisor" : {"version_url" : "https://api.github.com/repos/grycap/faas-supervisor/releases/latest",
                                                 "zip_url" : "https://github.com/grycap/faas-supervisor/archive/{0}.zip",
                                                 "default_version" : "master",
                                                 "layer_name" : "faas-supervisor"}
                },
                "udocker_info" : {
                    "zip_url" : "https://github.com/grycap/faas-supervisor/raw/master/extra/udocker.zip"
                },
            }, ...
        }
        '''
        self.client = lambda_client
        self.cfg_layer_info = ConfigFileParser().get_faas_supervisor_layer_info()
        self.supervisor_version = self.cfg_layer_info['default_version']
        self.supervisor_zip_url = self.cfg_layer_info['zip_url'].format(self.supervisor_version)        
        self.layer_name = self.cfg_layer_info['layer_name']
        self.layer_zip_path = utils.join_paths(utils.get_tmp_dir(), '{}.zip'.format(self.layer_name))
        
    def _create_tmp_folders(self):
        self.tmp_zip_folder = utils.create_tmp_dir()
        self.tmp_zip_path = self.tmp_zip_folder.name
        self.layer_code_folder = utils.create_tmp_dir()
        self.layer_code_path = self.layer_code_folder.name

    def _get_supervisor_version(self):
        j = json.loads(request.call_http_endpoint(self.cfg_layer_info['version_url']).text)
        return j['tag_name']        

    def _download_supervisor(self):
#         supervisor_version = self._get_supervisor_version()
        self.version_path = 'faas-supervisor-{0}'.format(self.supervisor_version)
        supervisor_zip = request.get_file(self.supervisor_zip_url)
        with zipfile.ZipFile(io.BytesIO(supervisor_zip)) as thezip:
            for file in thezip.namelist():
                if file.startswith('{}/extra'.format(self.version_path)) or \
                   file.startswith('{}/faassupervisor'.format(self.version_path)):
                    thezip.extract(file, self.tmp_zip_path)

    def _copy_supervisor_files(self):
        supervisor_path = utils.join_paths(self.tmp_zip_path, self.version_path, 'faassupervisor')
        shutil.move(supervisor_path, utils.join_paths(self.layer_code_path, 'python', 'faassupervisor'))
        
    def _copy_udocker_files(self):
        utils.unzip_folder(utils.join_paths(self.tmp_zip_path, self.version_path, 'extra', 'udocker.zip'), self.layer_code_path)
            
    def _create_layer_zip(self):
        utils.zip_folder(self.layer_zip_path, self.layer_code_path)
    
    def _get_supervisor_layer_props(self):
        return {'LayerName' : self.layer_name,
                'Description' : 'FaaS supervisor that allows to run containers in rootless environments',
                'Content' : { 'ZipFile': utils.read_file(self.layer_zip_path, mode="rb") },
                'LicenseInfo' : 'Apache 2.0'}    
    
    def is_supervisor_layer_created(self):
        return self.layer.exists(self.layer_name)    
    
    def _create_layer(self):
        self._create_tmp_folders()
        self._download_supervisor()        
        self._copy_supervisor_files()
        self._copy_udocker_files()
        self._create_layer_zip()
        supervisor_layer_props = self._get_supervisor_layer_props()
        self.supervisor_layer_info = self.layer.create(**supervisor_layer_props)
        utils.delete_file(self.layer_zip_path)        
    
    def create_supervisor_layer(self):
        logger.info("Creating faas-supervisor layer")
        self._create_layer()
        logger.info("Faas-supervisor layer created")        
        
    def update_supervisor_layer(self):
        logger.info("Updating faas-supervisor layer")
        self._create_layer()
        logger.info("Faas-supervisor layer updated")
        
    def get_layers_arn(self):
        layers = []
        if not hasattr(self, "supervisor_layer_info"):
            self.supervisor_layer_info = self.layer.get_info(self.layer_name)
            layers.append(self.supervisor_layer_info['LatestMatchingVersion']['LayerVersionArn'])
        else:
            layers.append(self.supervisor_layer_info['LayerVersionArn'])
        return layers
    
    def get_all_layers_info(self):
        result = []
        layers_info = self.client.list_layers()
        if 'Layers' in layers_info:
            result.extend(layers_info['Layers'])
        while 'NextMarker' in layers_info:
            layers_info = self.client.list_layers(Marker=layers_info['NextMarker'])
            if 'Layers' in layers_info:
                result.extend(layers_info['Layers'])            
        return result
    
    def print_layers_info(self):
        layers_info = self.get_all_layers_info()
        headers = ['NAME', 'VERSION', 'ARN', 'RUNTIMES']
        table = []
        for layer in layers_info:
            table.append([layer['LayerName'],
                          layer['LatestMatchingVersion']['Version'],
                          layer['LayerArn'],
                          layer['LatestMatchingVersion'].get('CompatibleRuntimes','-')])
        print(tabulate(table, headers))
        
    def get_latest_supervisor_layer_arn(self):
        self.supervisor_layer_info = self.layer.get_info(self.layer_name)
        return self.supervisor_layer_info['LatestMatchingVersion']['LayerVersionArn']
