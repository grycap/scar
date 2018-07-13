# SCAR - Serverless Container-aware ARchitectures
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

class ScarError(Exception):
    """
    The base exception class for ScarError exceptions.

    :ivar msg: The descriptive message associated with the error.
    """
    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs

class FunctionCreationError(ScarError):
    """
    An error occurred when creating the lambda function.

    :ivar name: Name of the function
    """
    fmt = "Unable to create the function '{function_name}' : {error_msg}"        

class FunctionNotFoundError(ScarError):
    """
    The requested function does not exist.

    :ivar name: Name of the function
    """
    fmt = "Unable to find the function '{function_name}' : {error_msg}"
    
    