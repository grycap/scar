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
default_aws_region = "us-east-1"

class BotoClient(object):
    
    def __init__(self, region=None):
        self.region = region 
        
    @utils.lazy_property
    def client(self):
        if self.region is None:
            self.region = default_aws_region
        boto_config = botocore.config.Config(read_timeout=botocore_client_read_timeout)            
        client = boto3.client(self.boto_client_name, region_name=self.region, config=boto_config)
        return client        
    
    def get_access_key(self):
        session = boto3.Session()
        credentials = session.get_credentials()
        return credentials.access_key
    
    def error_handler(self, fn):
        '''Decorator that makes a property lazy-evaluated.'''
        attr_name = '_lazy_' + fn.__name__
    
        @property
        def _lazy_property(self):
            if not hasattr(self, attr_name):
                setattr(self, attr_name, fn(self))
            return getattr(self, attr_name)
        return _lazy_property    
