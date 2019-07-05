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

from string import Template
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from scar.providers.aws import GenericClient
from scar.utils import GitHubUtils, StrUtils
import scar.exceptions as excp
import scar.logger as logger


class LaunchTemplates(GenericClient):
    """Class to manage the creation and update of launch templates."""

    _TEMPLATE_NAME = 'faas-supervisor'
    _SUPERVISOR_GITHUB_REPO = 'faas-supervisor'
    _SUPERVISOR_GITHUB_USER = 'grycap'
    _SUPERVISOR_GITHUB_ASSET_NAME = 'supervisor'

    # Script to download 'faas-supervisor'
    _LAUNCH_TEMPLATE_SCRIPT = Template(
        '#!/bin/bash\n'
        'mkdir -p /opt/faas-supervisor/bin\n'
        'curl $supervisor_binary_url -L -o /opt/faas-supervisor/bin/supervisor\n'
        'chmod +x /opt/faas-supervisor/bin/supervisor\n'
    )

    def __init__(self, aws_properties, supervisor_version):
        super().__init__(aws_properties)
        self.supervisor_version = supervisor_version
        if self.supervisor_version == 'latest':
            self.supervisor_version = GitHubUtils.get_latest_release(
                self._SUPERVISOR_GITHUB_USER,
                self._SUPERVISOR_GITHUB_REPO
            )

    @excp.exception(logger)
    def _is_supervisor_created(self) -> bool:
        """Checks if 'faas-supervisor' launch template is created"""
        params = {'Filters': [
            {'Name': 'launch-template-name',
             'Values': [self._TEMPLATE_NAME]}
        ]}
        response = self.client.describe_launch_templates(params)
        return ('LaunchTemplates' in response and
                response['LaunchTemplates'])

    @excp.exception(logger)
    def _is_supervisor_version_created(self) -> int:
        """Checks if the supervisor version specified is created.
        Returns the Launch Template version or -1 if it does not exists"""
        response = self.client.describe_launch_template_versions(
            {'LaunchTemplateName': self._TEMPLATE_NAME})
        versions = response['LaunchTemplateVersions']
        # Get ALL versions
        while ('NextToken' in response and response['NextToken']):
            response = self.client.describe_launch_template_versions(
                {'LaunchTemplateName': self._TEMPLATE_NAME,
                 'NextToken': response['NextToken']})
            versions.extend(response['LaunchTemplateVersions'])

        for version in versions:
            if 'VersionDescription' in version:
                if version['VersionDescription'] == self.supervisor_version:
                    return version['VersionNumber']
        return -1

    @excp.exception(logger)
    def _create_supervisor_user_data(self) -> str:
        """Returns the user_data with the script required for downloading
        the specified version of faas-supervisor in mime-multipart format
        and encoded in base64

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
                                        self.supervisor_version)
        script = self._LAUNCH_TEMPLATE_SCRIPT.substitute(
            supervisor_binary_url=url)
        content = MIMEText(script, 'x-shellscript')
        multipart.attach(content)
        return StrUtils.utf8_to_base64_string(str(multipart))

    @excp.exception(logger)
    def get_launch_template_version(self) -> int:
        """Return the launch template version of the specified version of
        'faas-supervisor'. If it does not exists creates a new one."""
        if self._is_supervisor_created():
            is_created = self._is_supervisor_version_created()
            if is_created is not -1:
                logger.info('Using existent \'faas-supervisor\' launch template.')
                return is_created
            else:
                logger.info((f"Creating launch template version with 'faas-supervisor' "
                             f"version '{self.supervisor_version}'."))
                user_data = self._create_supervisor_user_data()
                response = self.client.create_launch_template_version(
                    self._TEMPLATE_NAME,
                    self.supervisor_version,
                    {'UserData': user_data})
                return response['LaunchTemplateVersion']['VersionNumber']
        else:
            logger.info((f"Creating launch template with 'faas-supervisor' "
                         f"version '{self.supervisor_version}'."))
            user_data = self._create_supervisor_user_data()
            response = self.client.create_launch_template(
                self._TEMPLATE_NAME,
                self.supervisor_version,
                {'UserData': user_data})
            return response['LaunchTemplate']['LatestVersionNumber']
