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

import importlib
import scar.utils as utils

class GenericClient(object):
    
    src_path = 'scar.providers.aws.clients'
    clients = { 'APIGateway': {'module' : '{}.apigateway'.format(src_path), 'class_name' : 'APIGatewayClient'},
                'Batch': {'module' : '{}.batchfunction'.format(src_path), 'class_name' : 'BatchClient'},
                'CloudWatchLogs': {'module' : '{}.cloudwatchlogs'.format(src_path), 'class_name' : 'CloudWatchLogsClient'},
                'IAM': {'module' : '{}.iam'.format(src_path), 'class_name' : 'IAMClient'},
                'Lambda': {'module' : '{}.lambdafunction'.format(src_path), 'class_name' : 'LambdaClient'},
                'ResourceGroups': {'module' : '{}.resourcegroups'.format(src_path), 'class_name' : 'ResourceGroupsClient'},
                'S3': {'module' : '{}.s3'.format(src_path), 'class_name' : 'S3Client'},
                }

    def __init__(self, aws_properties):
        self.aws = aws_properties

    def get_client_args(self):
        return {'client' : {'region_name' : self.aws.region },
                'session' : { 'profile_name' : self.aws.boto_profile }}
    
    @utils.lazy_property
    def client(self):
        '''Dynamically loads the module and the client class needed'''
        client_name = self.__class__.__name__
        module = importlib.import_module(self.clients[client_name]['module'])
        class_ = getattr(module, self.clients[client_name]['class_name'])
        client = class_(**self.get_client_args())
        return client
