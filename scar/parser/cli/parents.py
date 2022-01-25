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


def create_function_definition_parser():
    function_definition_parser = argparse.ArgumentParser(add_help=False)
    function_definition_parser.add_argument("-d", "--description",
                                            help="Lambda function description.")
    function_definition_parser.add_argument("-e", "--environment",
                                            action='append',
                                            help=("Pass environment variable to the container "
                                                  "(VAR=val). Can be defined multiple times."))
    function_definition_parser.add_argument("-le", "--lambda-environment",
                                            action='append',
                                            help=("Pass environment variable to the lambda "
                                                  "function (VAR=val). Can be defined multiple "
                                                  "times."))
    function_definition_parser.add_argument("-m", "--memory",
                                            type=int,
                                            help=("Lambda function memory in megabytes. "
                                                  "Range from 128 to 3008 in increments of 64"))
    function_definition_parser.add_argument("-t", "--timeout",
                                            type=int,
                                            help=("Lambda function maximum execution "
                                                  "time in seconds. Max 900."))
    function_definition_parser.add_argument("-tt", "--timeout-threshold",
                                            type=int,
                                            help=("Extra time used to postprocess the data. "
                                                  "This time is extracted from the total "
                                                  "time of the lambda function."))
    function_definition_parser.add_argument("-ll", "--log-level",
                                            help=("Set the log level of the lambda function. "
                                                  "Accepted values are: "
                                                  "'CRITICAL','ERROR','WARNING','INFO','DEBUG'"))
    function_definition_parser.add_argument("-l", "--layers",
                                            action='append',
                                            help=("Pass layers ARNs to the lambda function. "
                                                  "Can be defined multiple times."))
    function_definition_parser.add_argument("-ib", "--input-bucket",
                                            help=("Bucket name where the input files "
                                                  "will be stored."))
    function_definition_parser.add_argument("-ob", "--output-bucket",
                                            help=("Bucket name where the output files are saved."))
    function_definition_parser.add_argument("-em", "--execution-mode",
                                            help=("Specifies the execution mode of the job. "
                                                  "It can be 'lambda', 'lambda-batch' or 'batch'"))
    function_definition_parser.add_argument("-r", "--iam-role",
                                            help=("IAM role used in the management of "
                                                  "the functions"))
    function_definition_parser.add_argument("-sv", "--supervisor-version",
                                            help=("FaaS Supervisor version. "
                                                  "Can be a tag or 'latest'."))
    function_definition_parser.add_argument("-rt", "--runtime", help="Lambda runtime")
    # Batch (job definition) options
    function_definition_parser.add_argument("-bm", "--batch-memory",
                                            help="Batch job memory in megabytes")
    function_definition_parser.add_argument("-bc", "--batch-vcpus",
                                            help=("Number of vCPUs reserved for the "
                                                  "Batch container"))
    function_definition_parser.add_argument("-g", "--enable-gpu",
                                            help=("Reserve one physical GPU for the Batch "
                                                  "container (if it's available in the "
                                                  "compute environment)"),
                                            action="store_true")
    return function_definition_parser


def create_exec_parser():
    exec_parser = argparse.ArgumentParser(add_help=False)
    exec_parser.add_argument("-a", "--asynchronous",
                             help="Launch an asynchronous function.",
                             action="store_true")
    exec_parser.add_argument("-o", "--output-file",
                             help="Save output as a file")
    return exec_parser


def create_output_parser():
    output_parser = argparse.ArgumentParser(add_help=False)
    output_parser.add_argument("-j", "--json",
                               help="Return data in JSON format",
                               action="store_true")
    output_parser.add_argument("-v", "--verbose",
                               help="Show the complete aws output in json format",
                               action="store_true")
    return output_parser


def create_profile_parser():
    profile_parser = argparse.ArgumentParser(add_help=False)
    profile_parser.add_argument("-pf", "--profile",
                                help="AWS profile to use")
    return profile_parser


def create_storage_parser():
    storage_parser = argparse.ArgumentParser(add_help=False)
    storage_parser.add_argument("-b", "--bucket",
                                help="Bucket to use as storage",
                                required=True)
    storage_parser.add_argument("-p", "--path",
                                help="Path of the file or folder",
                                required=True)
    return storage_parser
