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

from .aws import AWS
from .iam import IAM
from botocore.exceptions import ClientError
import logging

class ResourceGroups(AWS):
    '''A low-level client representing aws Resource Groups Tagging API.
    https://boto3.readthedocs.io/en/latest/reference/services/resourcegroupstaggingapi.html'''
    
    def __init__(self, region=None):
        super().__init__('resourcegroupstaggingapi', region)

    def get_lambda_functions_arn_list(self):
        arn_list = []
        try:
            # Creation of a function filter by tags
            user_id = IAM().get_user_name_or_id()
            tag_filters = [ { 'Key': 'owner', 'Values': [ user_id ] },
                            { 'Key': 'createdby', 'Values': ['scar'] } ]
            response = self.client.get_resources(TagFilters=tag_filters,
                                            TagsPerPage=100,
                                            ResourceTypeFilters=['lambda'])
    
            for function in response['ResourceTagMappingList']:
                arn_list.append(function['ResourceARN'])
    
            while ('PaginationToken' in response) and (response['PaginationToken']):
                response = self.client.get_resources(PaginationToken=response['PaginationToken'],
                                                TagFilters=tag_filters,
                                                TagsPerPage=100)
                for function in response['ResourceTagMappingList']:
                    arn_list.append(function['ResourceARN'])
        except ClientError as ce:
            print("Error getting function arn by tag")
            logging.error("Error getting function arn by tag: %s" % ce)
        return arn_list
        