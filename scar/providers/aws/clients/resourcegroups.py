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

from scar.providers.aws.clients.boto import BotoClient
import scar.exceptions as ex
import scar.logger as logger

class ResourceGroupsClient(BotoClient):
    '''A low-level client representing aws Resource Groups Tagging API.
    https://boto3.readthedocs.io/en/latest/reference/services/resourcegroupstaggingapi.html'''
    
    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 'resourcegroupstaggingapi'
    
    @ex.exception(logger)    
    def get_tagged_resources(self, tag_filters, resource_type_filters):
        '''Returns all the tagged resources that are associated with the specified tags (keys and values) located in 
        the specified region for the AWS account.
        https://boto3.readthedocs.io/en/latest/reference/services/resourcegroupstaggingapi.html#ResourceGroupsTaggingAPI.Client.get_resources'''
        resource_list = []
        kwargs = {"TagFilters" : tag_filters, "TagsPerPage" : 100, "ResourceTypeFilters" : resource_type_filters}
        response = self.client.get_resources(**kwargs)
        resource_list.append(response)
        while ('PaginationToken' in response) and (response['PaginationToken']):
            kwargs['PaginationToken'] = response['PaginationToken']
            response = self.client.get_resources(**kwargs)
            resource_list.append(response)
        return resource_list
        