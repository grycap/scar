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
from botocore.exceptions import ClientError
import utils.functionutils as utils

class IAM(AWS):
    '''A low-level client representing aws Identity and Access Management (IAM).
    https://boto3.readthedocs.io/en/latest/reference/services/iam.html'''    
    
    def __init__(self, region=None):
        super().__init__('iam', region)
        
    def get_user_name_or_id(self):
        try:
            user = self.client.get_user()['User']
            return user.get('UserName', user['UserId'])
        except ClientError as ce:
            # If the user doesn't have access rights to IAM
            return utils.find_expression('(?<=user\/)(\S+)', str(ce)) 
        