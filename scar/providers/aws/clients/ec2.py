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
"""Module with the class necessary to manage the
EC2 creation, deletion and configuration."""

from typing import Dict
from scar.providers.aws.clients import BotoClient
from scar.exceptions import exception
import scar.logger as logger


class EC2Client(BotoClient):
    """A low-level client representing Amazon Elastic Compute Cloud (EC2).
    DOC_URL: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'ec2'

    @exception(logger)
    def create_launch_template(self, name: str, description: str, data: Dict) -> Dict:
        """Creates a launch template.
        A launch template contains the parameters to launch an instance."""
        kwargs = {'LaunchTemplateName': name,
                  'VersionDescription': description,
                  'LaunchTemplateData': data}
        return self.client.create_launch_template(**kwargs)

    @exception(logger)
    def create_launch_template_version(self, name: str, description: str, data: Dict) -> Dict:
        """Creates a new version for a launch template.
        You can specify an existing version of launch template
        from which to base the new version."""
        kwargs = {'LaunchTemplateName': name,
                  'VersionDescription': description,
                  'LaunchTemplateData': data}
        return self.client.create_launch_template_version(**kwargs)

    @exception(logger)
    def describe_launch_templates(self, parameters: Dict) -> Dict:
        """Describes one or more launch templates."""
        return self.client.describe_launch_templates(**parameters)

    @exception(logger)
    def describe_launch_template_versions(self, parameters: Dict) -> Dict:
        """Describes one or more versions of a specified launch template."""
        return self.client.describe_launch_template_versions(**parameters)
