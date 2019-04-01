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

def call_http_endpoint(url, **kwargs):
    """
    Does a 'GET' or 'PUT' request if the parameter 'data' exists or not respectively

    :param url: URL for the request.        
    :param data: (optional) Dictionary (will be form-encoded), bytes, or file-like object to send in the body of the request.
    :param headers: (optional) Dictionary of HTTP Headers to send with the request.
    :param parameters: (optional) Dictionary or bytes to be sent in the query string.
    """
    if ('data' in kwargs and kwargs['data']) or ('json' in kwargs and kwargs['json']):
        response = requests.post(url, **kwargs)
    else:
        response = requests.get(url, **kwargs)
    return response

def get_file(url):
    response = requests.get(url)
    if response:
        return response.content
    