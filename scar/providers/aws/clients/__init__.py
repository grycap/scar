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
"""Module with the generic classes and methods used in the boto client modules."""

from typing import Dict
import boto3
import botocore
from scar.utils import lazy_property


class BotoClient():
    """Generic class in charge of creating a boto client based on the
    'boto_client_name' property of the class that inherits it."""

    _READ_TIMEOUT = 360
    _BOTO_CLIENT_NAME = ''

    def __init__(self, client_args: Dict):
        self.client_args = client_args.get('client', {})
        self.session_args = client_args.get('session', {})

    @lazy_property
    def client(self):
        """Returns a boto client based on the 'boto_client_name' property,
        the region specified on the client args and
        the profile specified on the session args."""
        # 'default' profile if nothing set
        session = boto3.Session(**self.session_args)
        self.client_args['config'] = botocore.config.Config(read_timeout=self._READ_TIMEOUT)
        return session.client(self._BOTO_CLIENT_NAME, **self.client_args)

    def get_access_key(self) -> str:
        """Returns the access key belonging to the boto_profile used."""
        session = boto3.Session(**self.session_args)
        credentials = session.get_credentials()
        return credentials.access_key
