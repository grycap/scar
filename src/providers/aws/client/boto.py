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

# Default values
botocore_client_read_timeout = 360
default_aws_region = "us-east-1"

class BotoClient(object):
    
    def __init__(self, client_name, region=None):
        if region is None:
            region = default_aws_region
        boto_config = botocore.config.Config(read_timeout=botocore_client_read_timeout)            
        self.__client = boto3.client(client_name, region_name=region, config=boto_config)        
    
    def get_access_key(self):
        session = boto3.Session()
        credentials = session.get_credentials()
        return credentials.access_key
    
    def get_client(self):
        return self.__client