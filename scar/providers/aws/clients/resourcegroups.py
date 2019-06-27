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
resource groups listing."""

from typing import List
from scar.providers.aws.clients import BotoClient
from scar.exceptions import exception
import scar.logger as logger


class ResourceGroupsClient(BotoClient):
    """A low-level client representing aws Resource Groups Tagging API.
    DOC_URL: https://boto3.readthedocs.io/en/latest/reference/
             services/resourcegroupstaggingapi.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'resourcegroupstaggingapi'

    @exception(logger)
    def get_tagged_resources(self, tag_filters: List,
                             resource_type_filters: List,
                             next_token: str = None) -> List:
        """Returns all the tagged resources that are associated with
        the specified tags (keys and values) located in the specified
        region for the AWS account."""
        resource_list = []
        kwargs = {"TagFilters" : tag_filters,
                  "ResourceTypeFilters" : resource_type_filters}
        if next_token:
            kwargs['PaginationToken'] = next_token
        response = self.client.get_resources(**kwargs)
        if 'ResourceTagMappingList' in response:
            resource_list.extend(response['ResourceTagMappingList'])
        # Retrieve all the remaining resources recursively
        if 'PaginationToken' in response and response['PaginationToken']:
            resource_list.extend(self.get_tagged_resources(tag_filters,
                                                           resource_type_filters,
                                                           kwargs['PaginationToken']))
        return resource_list
