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

from .boto import BotoClient
from botocore.exceptions import ClientError
import src.logger as logger
import src.utils as utils

class ResourceGroups():
    
    @utils.lazy_property
    def client(self):
        client = ResourceGroupsClient()
        return client

    def get_lambda_functions_arn_list(self, iam_user_id):
        arn_list = []
        try:
            # Creation of a function_info filter by tags
            tag_filters = [ { 'Key': 'owner', 'Values': [ iam_user_id ] },
                            { 'Key': 'createdby', 'Values': ['scar'] } ]
            resource_type_filters = ['lambda']
            tagged_resources = self.client.get_tagged_resources(tag_filters, resource_type_filters)
            for element in tagged_resources:
                for function_info in element['ResourceTagMappingList']:
                    arn_list.append(function_info['ResourceARN'])
        except ClientError as ce:
            logger.error("Error getting function_info arn by tag",
                         "Error getting function_info arn by tag: %s" % ce)
        return arn_list    
    
class ResourceGroupsClient(BotoClient):
    '''A low-level client representing aws Resource Groups Tagging API.
    https://boto3.readthedocs.io/en/latest/reference/services/resourcegroupstaggingapi.html'''
    
    def __init__(self, region=None):
        super().__init__('resourcegroupstaggingapi', region)

    def get_tagged_resources(self, tag_filters, resource_type_filters):
        '''Returns all the tagged resources that are associated 
        with the specified tags (keys and values) located in 
        the specified region for the AWS account.'''
        resource_list = []
        try:
            response = self.get_client().get_resources(TagFilters=tag_filters,
                                                       TagsPerPage=100,
                                                       ResourceTypeFilters=resource_type_filters)
            resource_list.append(response)
            while ('PaginationToken' in response) and (response['PaginationToken']):
                response = self.get_client().get_resources(PaginationToken=response['PaginationToken'],
                                                           TagFilters=tag_filters,
                                                           TagsPerPage=100,
                                                           ResourceTypeFilters=resource_type_filters)
                resource_list.append(response)
        except ClientError as ce:
            error_msg = "Error getting tagged resources"
            logger.error(error_msg, error_msg + ": %s" % ce)
        return resource_list
        