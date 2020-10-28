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
from typing import Dict
from scar.utils import DataTypesUtils

FAAS_PROVIDERS = ["aws", "oscar"]

def merge_conf(conf: Dict, yaml: Dict) -> Dict:
    result = yaml.copy()
    # We have to merge the default config with all the defined functions
    for provider in FAAS_PROVIDERS:
        for index, function in enumerate(result.get('functions', {}).get(provider, {})):
            result['functions'][provider][index] = \
                DataTypesUtils.merge_dicts_with_copy(conf.get(provider,{}), function)
    result['scar'] = DataTypesUtils.merge_dicts_with_copy(result.get('scar', {}),
                                                          conf.get('scar', {}))
    return result

def merge_cmd_yaml(cmd: Dict, yaml: Dict) -> Dict:
    result = yaml.copy()
    # We merge the cli commands with all the defined functions
    # CLI only allows define AWS parameters
    for cli_cmd in cmd.get('functions', {}).get("aws", {}):
        for index, function in enumerate(result.get('functions', {}).get("aws", {})):
            result['functions']['aws'][index] = \
                DataTypesUtils.merge_dicts_with_copy(function, cli_cmd)
    result['scar'] = DataTypesUtils.merge_dicts_with_copy(result.get('scar', {}),
                                                          cmd.get('scar', {}))
    result['storage_providers'] = DataTypesUtils.merge_dicts_with_copy(result.get('storage_providers', {}),
                                                                       cmd.get('storage_providers', {}))
    return result
