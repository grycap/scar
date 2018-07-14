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

from src.providers.aws.clients.boto import BotoClient
import src.logger as logger
import src.exceptions as ex

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
        