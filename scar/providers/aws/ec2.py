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
"""Module with methods to manage EC2 launch templates.

Generic response from boto3:
{'LaunchTemplates': [{'CreateTime': datetime.datetime(2019, 6, 18, 10, 9, 46, tzinfo=tzutc()),
              'CreatedBy': 'arn:aws:iam::XXX:user/test',
              'DefaultVersionNumber': 1,
              'LatestVersionNumber': 1,
              'LaunchTemplateId': 'lt-052fafdsf8bf047fa9',
              'LaunchTemplateName': 'test',
              'Tags': [{'Key': 'supervisor_version', 'Value': '121'}]}],
 'ResponseMetadata': {'HTTPHeaders': {'content-type': 'text/xml;charset=UTF-8',
                              'date': 'Tue, 18 Jun 2019 10:16:50 GMT',
                              'server': 'AmazonEC2',
                              'transfer-encoding': 'chunked',
                              'vary': 'accept-encoding'},
              'HTTPStatusCode': 200,
              'RequestId': 'XXX',
              'RetryAttempts': 0}}"""

from typing import Dict
from scar.providers.aws import GenericClient
import scar.exceptions as excp
import scar.logger as logger


def _get_launch_template_id(response: Dict) -> str:
    template_id = ''
    if 'LaunchTemplates' in response:
        templates = response['LaunchTemplates']
        if templates and 'LaunchTemplateId' in templates[0]:
            template_id = templates[0]['LaunchTemplateId']
    return template_id


def _get_launch_templates_supervisor_version(response: Dict) -> str:
    s_version = ''
    if 'LaunchTemplates' in response:
        templates = response['LaunchTemplates']
        if templates and 'Tags' in templates[0]:
            tags = templates[0]['Tags']
            if tags:
                s_version = tags[0]['Value']
    return s_version


class EC2(GenericClient):
    """Class to manage the creation and update of launch templates."""

    _TEMPLATE_NAME = 'faas-supervisor'
    _TAG_NAME = 'supervisor_version'

    @excp.exception(logger)
    def create_launch_template_and_tag(self, data: Dict, supervisor_version: str) -> Dict:
        """Creates the 'faas-supervisor' launch template and the supervisor version tag."""
        response = self.client.create_launch_template(self._TEMPLATE_NAME, data)
        template_id = _get_launch_template_id(response)
        self.client.create_tag(template_id, self._TAG_NAME, supervisor_version)
        return response

    @excp.exception(logger)
    def update_launch_template_and_tag(self, data: Dict, supervisor_version: str) -> Dict:
        """Updates the 'faas-supervisor' launch template and the supervisor version.
        Needs that the 'faas-supervisor' template already exists."""
        response = self.client.create_launch_template_version(self._TEMPLATE_NAME, data)
        template_id = _get_launch_template_id(response)
        self.client.create_tag(template_id, self._TAG_NAME, supervisor_version)
        return response

    @excp.exception(logger)
    def get_supervisor_version_of_launch_template(self) -> str:
        """Returns the supervisor version linked to the 'faas-supervisor' launch template."""
        response = self.client.describe_launch_templates(self._TEMPLATE_NAME)
        return _get_launch_templates_supervisor_version(response)
