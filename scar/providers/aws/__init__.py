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
"""Module with the generic classes and methods used in other aws classes"""

from typing import Dict
import scar.utils as utils
from scar.providers.aws.clients.apigateway import APIGatewayClient
from scar.providers.aws.clients.batchfunction import BatchClient
from scar.providers.aws.clients.cloudwatchlogs import CloudWatchLogsClient
from scar.providers.aws.clients.iam import IAMClient
from scar.providers.aws.clients.lambdafunction import LambdaClient
from scar.providers.aws.clients.resourcegroups import ResourceGroupsClient
from scar.providers.aws.clients.s3 import S3Client
from scar.providers.aws.clients.ec2 import EC2Client


class GenericClient():
    """Class in charge of creating the boto clients."""

    # pylint: disable=too-few-public-methods

    _CLIENTS = {'APIGATEWAY': APIGatewayClient,
                'BATCH': BatchClient,
                'CLOUDWATCHLOGS': CloudWatchLogsClient,
                'IAM': IAMClient,
                'LAMBDA': LambdaClient,
                'RESOURCEGROUPS': ResourceGroupsClient,
                'S3': S3Client,
                'EC2': EC2Client}

    def __init__(self, aws_properties: Dict):
        self.aws = aws_properties

    def _get_client_args(self):
        return {'client' : {'region_name' : self.aws.region},
                'session' : {'profile_name' : self.aws.boto_profile}}

    @utils.lazy_property
    def client(self):
        """Returns the required boto client based on the implementing class name."""
        client_name = self.__class__.__name__.upper()
        client = self._CLIENTS[client_name](**self._get_client_args())
        return client
