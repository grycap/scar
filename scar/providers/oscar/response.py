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

from typing import Dict, List
from tabulate import tabulate
from scar.providers.aws.response import OutputType
import scar.logger as logger
from scar.utils import StrUtils


def parse_ls_response(oscar_resources: List, endpoint: str, cluster_id: str, output_type: int) -> None:
    oscar_output = 'Services'
    result = []
    text_message = f'\nOSCAR SERVICES - CLUSTER "{cluster_id}" ({endpoint}):\n'
    for resources_info in oscar_resources:
        result.append(_parse_service_info(resources_info))
    text_message += _get_table(result)
    _print_generic_response({oscar_output: oscar_resources}, output_type, text_message, {oscar_output: result})


def parse_service_creation(resources_info: Dict, output_type: int) -> None:
    result = _parse_service_info(resources_info)
    text_message = f'Service \'{resources_info["name"]}\' successfully created on cluster \'{resources_info.get("cluster_id")}\'.'
    _print_generic_response(resources_info, output_type, text_message, result)


def parse_service_deletion(resources_info: Dict, output_type: int) -> None:
    result = _parse_service_info(resources_info)
    text_message = f'Service \'{resources_info.get("name")}\' successfully deleted from cluster \'{resources_info.get("cluster_id")}\'.'
    _print_generic_response(resources_info, output_type, text_message, result)


def _parse_service_info(resources_info: Dict) -> Dict:
    return {'Name': resources_info.get('name', '-'),
            'Memory': resources_info.get('memory', '-'),
            'CPU': resources_info.get('cpu', '-'),
            'Image_id': resources_info.get('image', '-')}


def _get_table(services_info: List) -> str:
    headers = ['NAME', 'MEMORY', 'CPU', 'IMAGE_ID']
    table = []
    for function in services_info:
        table.append([function['Name'],
                      function['Memory'],
                      function['CPU'],
                      function['Image_id']])
    return tabulate(table, headers)


def _print_generic_response(resources_info: Dict, output_type: int, text_message: str, json_output: Dict) -> None:
    # Support 'PLAIN_TEXT', 'JSON' and 'VERBOSE' output types
    if output_type == OutputType.PLAIN_TEXT.value:
        output = text_message
        logger.info(output)
    else:
        if output_type == OutputType.JSON.value:
            output = json_output
        elif output_type == OutputType.VERBOSE.value:
            output = resources_info
        logger.info_json(output)

