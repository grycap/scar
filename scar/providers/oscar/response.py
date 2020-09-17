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
"""Module with the class implementing the low-level functions to 
communicate with an OSCAR cluster."""

from typing import Dict
from tabulate import tabulate
from scar.providers.aws.response import OutputType
import scar.logger as logger

def parse_ls_response(oscar_resources: Dict, endpoint: str, cluster_id: str, output_type: int) -> None:
    # Only print the output if 'output_type' is 'PLAIN_TEXT'
    if output_type == OutputType.PLAIN_TEXT.value:
        result = []
        text_message = f'\nOSCAR SERVICES - CLUSTER "{cluster_id}" ({endpoint}):\n'
        for resources_info in oscar_resources:
            result.append(_parse_oscar_service_info(resources_info))
        text_message += _get_table(result)
        logger.info(text_message)

def _parse_oscar_service_info(resources_info: Dict) -> Dict:
    return {'Name': resources_info.get('name', '-'),
            'Memory': resources_info.get('memory', '-'),
            'CPU': resources_info.get('cpu', '-'),
            'Image_id': resources_info.get('image', '-')}

def _get_table(services_info: Dict) -> None:
    headers = ['NAME', 'MEMORY', 'CPU', 'IMAGE_ID']
    table = []
    for function in services_info:
        table.append([function['Name'],
                      function['Memory'],
                      function['CPU'],
                      function['Image_id']])
    return tabulate(table, headers)

