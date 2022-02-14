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
import argparse

FUNCTION_DEFINITION = "function_definition_parser"
OUTPUT = "output_parser"
PROFILE = "profile_parser"
EXEC = "exec_parser"
STORAGE = "storage_parser"

INIT_PARENTS = [PROFILE, FUNCTION_DEFINITION, OUTPUT]
INVOKE_PARENTS = [PROFILE, EXEC]
RUN_PARENTS = [PROFILE, EXEC, OUTPUT]
RM_LS_PARENTS = [PROFILE, OUTPUT]
LOG_PARENTS = [PROFILE]
PUT_GET_PARENTS = [PROFILE, STORAGE]


class Subparsers():

    def __init__(self, subparser, parents):
        self.subparser = subparser
        self.parent_parsers = parents

    def _get_parents(self, parent_sublist):
        return [self.parent_parsers.get(parent, "") for parent in parent_sublist]

    def add_subparser(self, name):
        getattr(self, f'_add_{name}_parser')()

    def _add_init_parser(self):
        init = self.subparser.add_parser('init',
                                         parents=self._get_parents(INIT_PARENTS),
                                         help="Create lambda function")
        # Set default function
        init.set_defaults(func="init")
        # Lambda conf
        group = init.add_mutually_exclusive_group(required=True)
        group.add_argument("-i", "--image",
                           help="Container image id (i.e. centos:7)")
        group.add_argument("-if", "--image-file",
                           help=("Container image file created with "
                                 "'docker save' (i.e. centos.tar.gz)"))
        group.add_argument("-f", "--conf-file",
                           help="Yaml file with the function configuration")
        init.add_argument("-n", "--name", help="Lambda function name")
        init.add_argument("-s", "--init-script", help=("Path to the input file "
                                                       "passed to the function"))
        init.add_argument("-ph", "--preheat",
                          help=("Invokes the function once and downloads the container"),
                          action="store_true")
        init.add_argument("-ep", "--extra-payload",
                          help=("Folder containing files that are going to be "
                                "added to the lambda function"))
        init.add_argument("-db", "--deployment-bucket",
                          help="Bucket where the deployment package is going to be uploaded.")
        # API Gateway conf
        init.add_argument("-api", "--api-gateway-name",
                          help="API Gateway name created to launch the lambda function")

    def _add_invoke_parser(self):
        invoke = self.subparser.add_parser('invoke',
                                           parents=self._get_parents(INVOKE_PARENTS),
                                           help="Call a lambda function using an HTTP request")
        # Set default function
        invoke.set_defaults(func='invoke')
        group = invoke.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name",
                           help="Lambda function name")
        group.add_argument("-f", "--conf-file",
                           help="Yaml file with the function configuration")
        invoke.add_argument("-db", "--data-binary",
                            help="File path of the HTTP data to POST.")
        invoke.add_argument("-jd", "--json-data",
                            help="JSON Body to Post")
        invoke.add_argument("-p", "--parameters",
                            help=("In addition to passing the parameters in the URL, "
                                  "you can pass the parameters here (i.e. '{\"key1\": "
                                  "\"value1\", \"key2\": [\"value2\", \"value3\"]}')."))

    def _add_run_parser(self):
        run = self.subparser.add_parser('run',
                                        parents=self._get_parents(RUN_PARENTS),
                                        help="Deploy function")
        # Set default function
        run.set_defaults(func='run')
        group = run.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name", help="Lambda function name")
        group.add_argument("-f", "--conf-file", help="Yaml file with the function configuration")
        run.add_argument("-s", "--run-script", help="Path to the script passed to the function")
        run.add_argument("-ib", "--input-bucket", help=("Bucket name with files to launch the function."))
        run.add_argument('c_args',
                         nargs=argparse.REMAINDER,
                         help="Arguments passed to the container.")

    def _add_rm_parser(self):
        rm = self.subparser.add_parser('rm',
                                       parents=self._get_parents(RM_LS_PARENTS),
                                       help="Delete function")
        # Set default function
        rm.set_defaults(func='rm')
        group = rm.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name",
                           help="Lambda function name")
        group.add_argument("-a", "--all",
                           help="Delete all lambda functions",
                           action="store_true")
        group.add_argument("-f", "--conf-file",
                        help="Yaml file with the function configuration")

    def _add_log_parser(self):
        log = self.subparser.add_parser('log',
                                        parents=self._get_parents(LOG_PARENTS),
                                        help="Show the logs for the lambda function")
        # Set default function
        log.set_defaults(func='log')
        group = log.add_mutually_exclusive_group(required=True)
        group.add_argument("-n", "--name",
                           help="Lambda function name")
        group.add_argument("-f", "--conf-file",
                           help="Yaml file with the function configuration")
        # CloudWatch args
        log.add_argument("-ls", "--log-stream-name",
                         help="Return the output for the log stream specified.")
        log.add_argument("-ri", "--request-id",
                         help="Return the output for the request id specified.")

    def _add_ls_parser(self):
        ls = self.subparser.add_parser('ls',
                                       parents=self._get_parents(RM_LS_PARENTS),
                                       help="List lambda functions")
        # Set default function
        ls.set_defaults(func='ls')
        # S3 args
        ls.add_argument("-b", "--bucket", help="Show bucket files")

    def _add_put_parser(self):
        put = self.subparser.add_parser('put',
                                        parents=self._get_parents(PUT_GET_PARENTS),
                                        help="Upload file(s) to bucket")
        # Set default function
        put.set_defaults(func='put')

    def _add_get_parser(self):
        get = self.subparser.add_parser('get',
                                        parents=self._get_parents(PUT_GET_PARENTS),
                                        help="Download file(s) from bucket")
        # Set default function
        get.set_defaults(func='get')

