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

import os
import src.utils as utils

aws_src_path = os.path.dirname(os.path.abspath(__file__))
lambda_code_files_path = utils.join_paths(aws_src_path, "cloud/lambda/")
scar_zip_path = utils.join_paths(lambda_code_files_path, "scar.zip")

def get_scar_layer_props():
    return {'LayerName' : 'scar',
            'Description' : 'SCAR supervisor',
            'Content' : { 'ZipFile': utils.read_file(scar_zip_path, mode="rb") },
            'CompatibleRuntimes' : ['python3.6','python3.7'],
            'LicenseInfo' : 'Apache 2.0'}