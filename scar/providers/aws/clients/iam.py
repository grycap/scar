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
from scar.providers.aws.clients.boto import BotoClient
import scar.exceptions as excp
import scar.logger as logger
import scar.utils as utils

class IAMClient(BotoClient):
    '''A low-level client representing aws Identity and Access Management (IAMClient).
    https://boto3.readthedocs.io/en/latest/reference/services/iam.html'''    
 
    # Parameter used by the parent to create the appropriate boto3 client
    boto_client_name = 'iam'
        
    @excp.exception(logger)         
    def get_user_info(self):
        '''
        Retrieves information about the specified IAM user, including the user's creation date, path, unique ID, and ARN.
        https://boto3.readthedocs.io/en/latest/reference/services/iam.html#IAM.Client.get_user
        '''
        try:
            return self.client.get_user()
        except ClientError as ce:
            if ce.response['Error']['Code'] == 'AccessDenied':
                # If the user doesn't have access rights to IAMClient
                # we can find the user name in the error response
                user_name = utils.find_expression(str(ce), '(?<=user\/)(\S+)')
                return {'UserName' : user_name,
                        'User' : {'UserName' : user_name, 'UserId' : ''}}
            else:
                raise
        except Exception as ex:
            raise excp.GetUserInfoError(error_msg=ex)
