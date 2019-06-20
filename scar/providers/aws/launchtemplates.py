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
from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from scar.providers.aws import GenericClient
from scar.utils import GitHubUtils, StrUtils
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


class LaunchTemplates(GenericClient):
    """Class to manage the creation and update of launch templates."""

    _TEMPLATE_NAME = 'faas-supervisor'
    _TAG_NAME = 'supervisor_version'
    _SUPERVISOR_GITHUB_REPO = 'faas-supervisor'
    _SUPERVISOR_GITHUB_USER = 'grycap'
    _SUPERVISOR_GITHUB_ASSET_NAME = 'supervisor'

    # Script to download 'faas-supervisor'
    _LAUNCH_TEMPLATE_SCRIPT = Template('#!/bin/bash\n'
                                       'mkdir -p /opt/faas-supervisor/bin\n'
                                       'curl $supervisor_binary_url -L -o /opt/faas-supervisor/bin/supervisor\n'
                                       'chmod +x /opt/faas-supervisor/bin/supervisor')

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

    def _create_supervisor_user_data(self, supervisor_version: str) -> str:
        """Returns the user_data with the script required for downloading the specified
        version of faas-supervisor in mime-multipart format and encoded in base64

        Generic mime-multipart file:
        Content-Type: multipart/mixed; boundary="===============3595946014116037730=="
        MIME-Version: 1.0

        --===============3595946014116037730==
        Content-Type: text/x-shellscript; charset="us-ascii"
        MIME-Version: 1.0
        Content-Transfer-Encoding: 7bit

        #!/bin/bash
        mkdir -p /opt/faas-supervisor/bin
        curl https://github.com/grycap/faas-supervisor/releases/download/1.0.11/supervisor -L -o /opt/faas-supervisor/bin/supervisor
        chmod +x /opt/faas-supervisor/bin/supervisor
        --===============3595946014116037730==--"""
        multipart = MIMEMultipart()
        url = GitHubUtils.get_asset_url(self._SUPERVISOR_GITHUB_USER,
                                        self._SUPERVISOR_GITHUB_REPO,
                                        self._SUPERVISOR_GITHUB_ASSET_NAME,
                                        supervisor_version)
        script = self._LAUNCH_TEMPLATE_SCRIPT.substitute(supervisor_binary_url=url)
        content = MIMEText(script, 'x-shellscript')
        multipart.attach(content)
        return StrUtils.utf8_to_base64_string(str(multipart))
