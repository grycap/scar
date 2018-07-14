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

from botocore.exceptions import ClientError
import src.logger as logger
from src.providers.aws.botoclientfactory import GenericClient

class ResourceGroups(GenericClient):
    
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
    
