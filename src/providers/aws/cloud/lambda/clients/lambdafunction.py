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

# Works in lambda environment
import src.utils as utils
logger = utils.get_logger()

class Lambda():

    def __init__(self, event, context):
        self.event = event
        self.context = context
        self.request_id = context.aws_request_id
        self.memory = int(context.memory_limit_in_mb)
        self.arn = context.invoked_function_arn
        self.function_name = context.function_name
        self.temporal_folder = "/tmp/{0}".format(self.request_id)
        self.input_folder = "{0}/input".format(self.temporal_folder)
        self.output_folder = "{0}/output".format(self.temporal_folder)
        self.permanent_folder = "/var/task"         
        self.log_group_name = self.context.log_group_name
        self.log_stream_name = self.context.log_stream_name            

    @utils.lazy_property
    def output_bucket(self):
        output_bucket = utils.get_environment_variable('OUTPUT_BUCKET')
        return output_bucket
    
    @utils.lazy_property
    def output_bucket_folder(self):
        output_bucket_folder = utils.get_environment_variable('OUTPUT_FOLDER')
        return output_bucket_folder
    
    @utils.lazy_property
    def input_bucket(self):
        input_bucket = utils.get_environment_variable('INPUT_BUCKET')
        return input_bucket
    
    def has_output_bucket(self):
        return utils.is_variable_in_environment('OUTPUT_BUCKET')

    def has_output_bucket_folder(self):
        return utils.is_variable_in_environment('OUTPUT_FOLDER')
    
    def has_input_bucket(self):
        return utils.is_variable_in_environment('INPUT_BUCKET')

    def get_invocation_remaining_seconds(self):
        return int(self.context.get_remaining_time_in_millis() / 1000) - int(utils.get_environment_variable('TIMEOUT_THRESHOLD'))
    