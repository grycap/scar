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
"""Module with methods and classes in charge
of parsing the SCAR CLI commands."""

import argparse
import sys
from typing import Dict, List
from scar.parser.cli.subparsers import Subparsers
from scar.parser.cli.parents import *
from scar.utils import DataTypesUtils, StrUtils
import scar.exceptions as excp
import scar.logger as logger
import scar.version as version


def _parse_aws_args(cmd_args: Dict) -> Dict:
    aws_args = {}
    other_args = [('profile', 'boto_profile'), 'region', 'execution_mode']
    _set_args(aws_args, 'iam', _parse_iam_args(cmd_args))
    _set_args(aws_args, 'lambda', _parse_lambda_args(cmd_args))
    _set_args(aws_args, 'batch', _parse_batch_args(cmd_args))
    _set_args(aws_args, 'cloudwatch', _parse_cloudwatchlogs_args(cmd_args))
    _set_args(aws_args, 'api_gateway', _parse_api_gateway_args(cmd_args))
    aws_args.update(DataTypesUtils.parse_arg_list(other_args, cmd_args))
    storage = _parse_s3_args(aws_args, cmd_args)
    result = {'functions': {'aws': [aws_args]}}
    if storage:
        result.update(storage)
    return result


def _set_args(args: Dict, key: str, val: str) -> None:
    if key and val:
        args[key] = val


def _parse_scar_args(cmd_args: Dict) -> Dict:
    scar_args = ['func', 'conf_file', 'json',
                 'verbose', 'path',
                 'preheat', 'execution_mode',
                 'output_file', 'supervisor_version']
    return {'scar' : DataTypesUtils.parse_arg_list(scar_args, cmd_args)}


def _parse_iam_args(cmd_args: Dict) -> Dict:
    iam_args = [('iam_role', 'role')]
    return DataTypesUtils.parse_arg_list(iam_args, cmd_args)


def _parse_lambda_args(cmd_args: Dict) -> Dict:
    lambda_arg_list = ['name', 'asynchronous', 'init_script', 'run_script', 'c_args', 'memory',
                       'timeout', 'timeout_threshold', 'image', 'image_file', 'description',
                       'lambda_role', 'extra_payload', ('environment', 'environment_variables'),
                       'layers', 'lambda_environment', 'list_layers', 'all', 'log_level']
    lambda_args = DataTypesUtils.parse_arg_list(lambda_arg_list, cmd_args)
    # Standardize log level if defined
    if "log_level" in lambda_args:
        lambda_args['log_level'] = lambda_args['log_level'].upper()
    # Parse environment variables
    lambda_args.update(_get_lambda_environment_variables(lambda_args))
    return lambda_args


def _get_lambda_environment_variables(lambda_args: Dict) -> None:
    lambda_env_vars = {}
    if "environment_variables" in lambda_args:
        # These variables define the udocker container environment variables
        lambda_env_vars['container'] = {'environment_variables' : {}}
        for env_var in lambda_args["environment_variables"]:
            key_val = env_var.split("=")
            # Add an specific prefix to be able to find the container variables defined by the user
            lambda_env_vars['container']['environment_variables'][f'{key_val[0]}'] = key_val[1]
        del(lambda_args['environment_variables'])
    if "extra_payload" in lambda_args:
        lambda_env_vars['container']['extra_payload'] = f"/var/task"
    if "init_script" in lambda_args:
        lambda_env_vars['container']['init_script'] = f"/var/task/init_script.sh"
    if "image" in lambda_args:
        lambda_env_vars['container']['image'] = lambda_args.get('image')
        del(lambda_args['image'])

    if "lambda_environment" in lambda_args:
        # These variables define the lambda environment variables
        lambda_env_vars['environment'] = {'Variables' : {}}
        for env_var in lambda_args["lambda_environment"]:
            key_val = env_var.split("=")
            lambda_env_vars['environment']['Variables'][f'{key_val[0]}'] = key_val[1]
        del(lambda_args['lambda_environment'])
    return lambda_env_vars


def _parse_batch_args(cmd_args: Dict) -> Dict:
    batch_args = [('batch_vcpus', 'vcpus'), ('batch_memory', 'memory'), 'enable_gpu']
    return DataTypesUtils.parse_arg_list(batch_args, cmd_args)


def _parse_cloudwatchlogs_args(cmd_args: Dict) -> Dict:
    cw_log_args = ['log_stream_name', 'request_id']
    return DataTypesUtils.parse_arg_list(cw_log_args, cmd_args)


def _parse_s3_args(aws_args: Dict, cmd_args: Dict) -> Dict:
    s3_arg_list = ['deployment_bucket',
               'input_bucket',
               'output_bucket',
               ('bucket', 'input_bucket')]

    s3_args = DataTypesUtils.parse_arg_list(s3_arg_list, cmd_args)
    storage = {}
    if s3_args:
        s3_id = StrUtils.get_random_uuid4_str()
        if 'deployment_bucket' in s3_args:
            aws_args['lambda']['deployment_bucket'] = s3_args['deployment_bucket']
        if 'input_bucket' in s3_args:
            aws_args['lambda']['input'] = [{'storage_name' : s3_id, 'path':  s3_args['input_bucket']}]
        if 'output_bucket' in s3_args:
            aws_args['lambda']['output'] = [{'storage_name' : s3_id, 'path':  s3_args['output_bucket']}]
        storage['storages'] = {'s3': [{'name': s3_id}]}
    return storage


def _parse_api_gateway_args(cmd_args: Dict) -> Dict:
    api_gtw_args = [('api_gateway_name', 'name'), 'parameters', 'data_binary', 'json_data']
    return DataTypesUtils.parse_arg_list(api_gtw_args, cmd_args)


def _create_main_parser():
    parser = argparse.ArgumentParser(prog="scar",
                                     description=("Deploy containers "
                                                  "in serverless architectures"),
                                     epilog=("Run 'scar COMMAND --help' "
                                             "for more information on a command."))
    parser.add_argument('--version',
                        help='Show SCAR version.',
                        dest="version",
                        action="store_true",
                        default=False)
    return parser


def _create_parent_parsers() -> Dict:
    parsers = {}
    parsers['function_definition_parser'] = create_function_definition_parser()
    parsers['exec_parser'] = create_exec_parser()
    parsers['output_parser'] = create_output_parser()
    parsers['profile_parser'] = create_profile_parser()
    parsers['storage_parser'] = create_storage_parser()
    return parsers


class CommandParser():
    """Class to manage the SCAR CLI commands."""

    def __init__(self, scar_cli):
        self.scar_cli = scar_cli
        self.parser = _create_main_parser()
        self.parent_parsers = _create_parent_parsers()
        self._add_subparsers()

    def _add_subparsers(self) -> None:
        subparsers = Subparsers(self.parser.add_subparsers(title='Commands'), self.parent_parsers)
        subparsers.add_subparser('init', self.scar_cli.init)
        subparsers.add_subparser('invoke', self.scar_cli.invoke)
        subparsers.add_subparser('run', self.scar_cli.run)
        subparsers.add_subparser('update', self.scar_cli.update)
        subparsers.add_subparser('rm', self.scar_cli.rm)
        subparsers.add_subparser('ls', self.scar_cli.ls)
        subparsers.add_subparser('log', self.scar_cli.log)
        subparsers.add_subparser('put', self.scar_cli.put)
        subparsers.add_subparser('get', self.scar_cli.get)

    @excp.exception(logger)
    def parse_arguments(self) -> Dict:
        """Command parsing and selection"""
        try:
            cmd_args = self.parser.parse_args()
            if cmd_args.version:
                print(f"SCAR {version.__version__}")
                sys.exit(0)

            cmd_args = vars(cmd_args)
            if 'func' not in cmd_args:
                raise excp.MissingCommandError()
            scar_args = _parse_scar_args(cmd_args)
            aws_args = _parse_aws_args(cmd_args)
            import pprint
            print("--------------------------------------------SCAR---------------------------------------")
            pprint.pprint(scar_args)
            print("--------------------------------------------AWS---------------------------------------")
            pprint.pprint(aws_args)
            print("-----------------------------------------------------------------------------------------")

            return DataTypesUtils.merge_dicts_with_copy(scar_args, aws_args)
        except AttributeError as aerr:
            logger.error("Incorrect arguments: use scar -h to see the options available",
                         f"Error parsing arguments: {aerr}")
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise
