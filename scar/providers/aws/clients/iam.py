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
IAM creation, deletion and configuration."""

from typing import Dict
from botocore.exceptions import ClientError
from scar.providers.aws.clients import BotoClient
from scar.exceptions import exception, GetUserInfoError
import scar.logger as logger
from scar.utils import StrUtils


class IAMClient(BotoClient):
    """A low-level client representing aws Identity and Access Management (IAMClient).
    DOC_URL: https://boto3.readthedocs.io/en/latest/reference/services/iam.html"""

    # Parameter used by the parent to create the appropriate boto3 client
    _BOTO_CLIENT_NAME = 'iam'
    _USER_NAME_REGEX = r'(?<=user\/)(\S+)'

    @exception(logger)
    def get_user_info(self) -> Dict:
        """Retrieves information about the specified IAM user,
        including the user's creation date, path, unique ID, and ARN."""
        try:
            return self.client.get_user()
        except ClientError as cerr:
            if cerr.response['Error']['Code'] == 'AccessDenied':
                # If the user doesn't have access rights to IAMClient
                # we can find the user name in the error response
                user_name = StrUtils.find_expression(str(cerr), self._USER_NAME_REGEX)
                return {'UserName' : user_name,
                        'User' : {'UserName' : user_name,
                                  'UserId' : ''}}
            raise cerr
        except Exception as ex:
            raise GetUserInfoError(error_msg=ex)
