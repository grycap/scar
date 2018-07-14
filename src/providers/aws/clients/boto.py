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

import boto3
import botocore
import src.utils as utils

# Default values
botocore_client_read_timeout = 360

class BotoClient(object):
    
    def __init__(self, **kwargs):
        self.session_args = kwargs['session']
        self.client_args = kwargs['client']
        
    @utils.lazy_property
    def client(self):
        session = boto3.Session(**self.session_args)
        self.client_args['config'] = botocore.config.Config(read_timeout=botocore_client_read_timeout)
        return session.client(self.boto_client_name, **self.client_args)
    
    def get_access_key(self):
        session = boto3.Session(**self.session_args)
        credentials = session.get_credentials()
        return credentials.access_key
