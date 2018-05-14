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

import requests
import src.logger as logger
import src.utils as utils

def invoke_function(url, method='GET', parameters=None, data=None, headers=None):
    if method == "GET":
        response = requests.get(url, headers=headers, params=parameters)
    elif method == "POST":
        response = requests.post(url, headers=headers, data=data, params=parameters)
    else:
        error_msg = "HTTP request '{0}' not recognized. Please use only 'GET' or 'POST'".format(method)
        logger.error(error_msg)
        utils.finish_failed_execution()
    return response