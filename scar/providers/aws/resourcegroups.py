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

from botocore.exceptions import ClientError
from scar.providers.aws.botoclientfactory import GenericClient
import scar.logger as logger

class ResourceGroups(GenericClient):
    
    def __init__(self, aws_properties):
        super().__init__(aws_properties)

    def get_lambda_functions_arn_list(self, iam_user_id):
        try:
            # Creation of a function_info filter by tags
            tag_filters = [ { 'Key': 'owner', 'Values': [ iam_user_id ] },
                            { 'Key': 'createdby', 'Values': ['scar'] } ]
            resource_type_filters = ['lambda']
            tagged_resources = self.client.get_tagged_resources(tag_filters, resource_type_filters)
            return [function_info['ResourceARN'] for element in tagged_resources \
                    for function_info in element['ResourceTagMappingList']]
        except ClientError as ce:
            logger.error("Error getting function_info arn by tag",
                         "Error getting function_info arn by tag: {}".format(ce))
    
