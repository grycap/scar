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
"""Module with methods and classes to manage AWS Resource Groups"""

from typing import List
from botocore.exceptions import ClientError
from scar.providers.aws import GenericClient
import scar.logger as logger


class ResourceGroups(GenericClient):
    """Class to manage AWS Resource Groups"""

    def __init__(self, resources_info) -> None:
        super().__init__(resources_info.get('lambda'))

    def get_resource_arn_list(self, iam_user_id: str, resource_type: str = 'lambda') -> List:
        """Returns a list of ARNs filtered by the resource_type
        passed and the tags created by scar."""
        try:
            # Creation of a function_info filter by tags
            tag_filters = [{'Key': 'owner', 'Values': [iam_user_id]},
                           {'Key': 'createdby', 'Values': ['scar']}]
            resource_type_filters = [resource_type]
            tagged_resources = self.client.get_tagged_resources(tag_filters, resource_type_filters)
            return [function_info['ResourceARN'] for function_info in tagged_resources]
        except ClientError as cerr:
            logger.error("Error getting function_info arn by tag",
                         f"Error getting function_info arn by tag: {cerr}")
            raise cerr
