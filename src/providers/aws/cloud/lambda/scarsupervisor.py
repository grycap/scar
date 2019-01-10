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

import json
import traceback
import faassupervisor.utils as utils
from faassupervisor.supervisor import Supervisor

logger = utils.get_logger()
logger.info('SCAR: Loading lambda function')

def lambda_handler(event, context):
    logger.debug("Received event: " + json.dumps(event))
    supervisor = Supervisor('lambda', event=event, context=context)
    try:
        supervisor.parse_input()
        supervisor.execute_function()                                      
        supervisor.parse_output()

    except Exception:
        exception_msg = traceback.format_exc()
        logger.error("Exception launched:\n {0}".format(exception_msg))
        return supervisor.create_error_response(exception_msg, 500)
    
    return supervisor.create_response()
