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

from typing import Dict
from scar.providers.aws.clients.boto import BotoClient
import scar.exceptions as excp
import scar.logger as logger


class EC2Client(BotoClient):
    """A low-level client representing Amazon Elastic Compute Cloud (EC2).
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 'ec2'

    @excp.exception(logger)
    def create_launch_template(self, name: str, data: Dict) -> Dict:
        """
        Creates a launch template.
        A launch template contains the parameters to launch an instance.

        https://boto3.amazonaws.com/v1/documentation/api/latest/reference
        /services/ec2.html#EC2.Client.create_launch_template"""
        kwargs = {'LaunchTemplateName': name,
                  'LaunchTemplateData': {'UserData' : data,
                                         'TagSpecifications': [{
                                             'ResourceType' : 'launch-template',
                                             'Tags': [{'Key': 'supervisor_version',
                                                       'Value': '115'}]}]}}
        return self.client.create_launch_template(**kwargs)

    @excp.exception(logger)
    def create_tag(self, resource_id: str, tag_key: str, tag_value: str) -> Dict:
        """
        Adds or overwrites the specified tags for the specified Amazon EC2 resource or resources.

        https://boto3.amazonaws.com/v1/documentation/api/latest/reference
        /services/ec2.html#EC2.Client.create_tags"""
        kwargs = {'Resources': [resource_id],
                  'Tags': [{'Key': tag_key, 'Value': tag_value}]}
        return self.client.create_tags(**kwargs)

    @excp.exception(logger)
    def create_launch_template_version(self, name: str, data: Dict) -> Dict:
        """
        Creates a new version for a launch template.
        You can specify an existing version of launch template from which to base the new version.

        https://boto3.amazonaws.com/v1/documentation/api/latest/reference
        /services/ec2.html#EC2.Client.create_launch_template_version"""
        kwargs = {'LaunchTemplateName': name,
                  'LaunchTemplateData': data}
        return self.client.create_launch_template_version(**kwargs)

    @excp.exception(logger)
    def describe_launch_templates(self, name: str) -> Dict:
        """
        Describes one or more launch templates.

        https://boto3.amazonaws.com/v1/documentation/api/latest/reference
        /services/ec2.html#EC2.Client.describe_launch_templates"""
        kwargs = {'LaunchTemplateNames': [name]}
        return self.client.describe_launch_templates(**kwargs)
    
    @excp.exception(logger)
    def describe_launch_template_versions(self, name: str, version: str) -> Dict:
        """
        Describes one or more versions of a specified launch template.

        https://boto3.amazonaws.com/v1/documentation/api/latest/reference
        /services/ec2.html#EC2.Client.describe_launch_template_versions"""
        kwargs = {'LaunchTemplateName': name,
                  'Versions': [version]}
        return self.client.describe_launch_template_versions(**kwargs)

