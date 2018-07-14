# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) 2011 - GRyCAP - Universitat Politecnica de Valencia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import src.utils as utils
from src.providers.aws.clients.lambdafunction import LambdaClient
from src.providers.aws.clients.apigateway import APIGatewayClient
from src.providers.aws.clients.cloudwatchlogs import CloudWatchLogsClient
from src.providers.aws.clients.iam import IAMClient
from src.providers.aws.clients.resourcegroups import ResourceGroupsClient
from src.providers.aws.clients.s3 import S3Client

class GenericClient(object):

    def __init__(self, aws_properties):
        self.aws_properties = aws_properties

    def get_client_args(self):
        return {'client' : {'region_name' : self.aws_properties['region'] } ,
                'session' : { 'profile_name' : self.aws_properties['boto_profile'] }}
    
    @utils.lazy_property
    def client(self):
        client_name = self.__class__.__name__ + 'Client'
        client = globals()[client_name](**self.get_client_args())
        return client

