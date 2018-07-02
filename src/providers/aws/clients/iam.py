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
from botocore.exceptions import ClientError
import src.logger as logger
import src.utils as utils

class IAMClient(BotoClient):
    '''A low-level client representing aws Identity and Access Management (IAMClient).
    https://boto3.readthedocs.io/en/latest/reference/services/iam.html'''    
 
    boto_client_name = 'iam'
        
    @utils.exception(logger)         
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
