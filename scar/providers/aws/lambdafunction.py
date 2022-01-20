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

import base64
import json
import io
import os
from typing import Dict
from multiprocessing.pool import ThreadPool
from zipfile import ZipFile, BadZipfile
import yaml
import docker
import time
from botocore.exceptions import ClientError
from scar.http.request import call_http_endpoint, get_file
from scar.providers.aws import GenericClient
from scar.providers.aws.functioncode import FunctionPackager, create_function_config
from scar.providers.aws.lambdalayers import LambdaLayers
from scar.providers.aws.s3 import S3
from scar.providers.aws.ecr import ECR
from scar.providers.aws.validators import AWSValidator
import scar.exceptions as excp
import scar.logger as logger
from scar.utils import DataTypesUtils, FileUtils, StrUtils, SupervisorUtils
from scar.parser.cfgfile import ConfigFileParser


MAX_CONCURRENT_INVOCATIONS = 500
ASYNCHRONOUS_CALL = {"invocation_type": "Event",
                     "log_type": "None",
                     "asynchronous": "True"}
REQUEST_RESPONSE_CALL = {"invocation_type": "RequestResponse",
                         "log_type": "Tail",
                         "asynchronous": "False"}


class Lambda(GenericClient):

    def __init__(self, resources_info: Dict) -> None:
        super().__init__(resources_info.get('lambda', {}))
        self.resources_info = resources_info
        self.function = resources_info.get('lambda', {})
        self.supervisor_version = resources_info.get('lambda').get('supervisor').get('version')

    def _get_creations_args(self, zip_payload_path: str, supervisor_zip_path: str) -> Dict:
        args = {'FunctionName': self.function.get('name'),
                'Role': self.resources_info.get('iam').get('role'),
                'Environment': self.function.get('environment'),
                'Description': self.function.get('description'),
                'Timeout':  self.function.get('timeout'),
                'MemorySize': self.function.get('memory'),
                'Tags': self.function.get('tags')}
        if self.function.get('runtime') == "image":
            args['Code'] = {'ImageUri': self.function.get('container').get('image')}
            args['PackageType'] = 'Image'
        else:
            args['Code'] = self._get_function_code(zip_payload_path, supervisor_zip_path)
            args['Runtime'] = self.function.get('runtime')
            args['Handler'] = self.function.get('handler')
            args['Layers'] = self.function.get('layers')
        return args

    def is_asynchronous(self):
        return self.function.get('asynchronous', False)

    def get_access_key(self) -> str:
        """Returns the access key belonging to the boto_profile used."""
        return self.client.get_access_key()

    def _delete_ecr_image(self):
        """Delete the ECR repository created in _create_ecr_image function."""
        ecr_cli = ECR(self.resources_info)
        repo_name = self.function.get('name')
        if ecr_cli.get_repository_uri(repo_name):
            logger.info('Deleting ECR repo: %s' % repo_name)
            ecr_cli.delete_repository(repo_name)

    def _create_dockerfile_ecr_image(self, init_script_path):
        """Create dockerfile to generate the new ECR image."""
        dockerfile = 'from %s\n' % self.function.get('container').get('image')
        dockerfile += 'ARG FUNCTION_DIR="/var/task"\n'
        dockerfile += 'RUN mkdir -p ${FUNCTION_DIR}\n'
        dockerfile += 'WORKDIR ${FUNCTION_DIR}\n'
        dockerfile += 'ENV PATH="${FUNCTION_DIR}:${PATH}"\n'
        # Add PYTHONIOENCODING to avoid UnicodeEncodeError as sugested in:
        # https://github.com/aws/aws-lambda-python-runtime-interface-client/issues/19
        dockerfile += 'ENV PYTHONIOENCODING="utf8"\n'

        # Add user environment variables
        if self.resources_info.get('lambda').get('container').get('environment').get('Variables', False):
            for key, value in self.resources_info.get('lambda').get('container').get('environment').get('Variables').items():
                dockerfile += 'ENV %s="%s"\n' % (key, value)

        dockerfile += 'CMD [ "supervisor" ]\n'
        dockerfile += 'ADD supervisor ${FUNCTION_DIR}\n'
        dockerfile += 'COPY function_config.yaml ${FUNCTION_DIR}\n'
        if init_script_path:
            dockerfile += 'COPY %s ${FUNCTION_DIR}\n' % FileUtils.get_file_name(init_script_path)
        return dockerfile

    def _ecr_image_name_prepared(self):
        """If the user set an already prepared image return the image name."""
        image_name = self.function.get('container').get('image')
        if ":" not in image_name:
            image_name = "%s:latest" % image_name
        if not self.function.get('container').get('create_image') and ".dkr.ecr." in image_name:
            logger.info('Image already prepared in ECR.')
            return image_name
        return None

    def _create_ecr_image(self, supervisor_path):
        """Creates an ECR image using the user provided image adding the supervisor tools."""
        # If the user set an already prepared image return the image name
        image_name = self._ecr_image_name_prepared()
        if image_name:
            return image_name

        client = docker.from_env()
        tmp_folder = FileUtils.create_tmp_dir()

        # Create function config file
        FileUtils.write_yaml(FileUtils.join_paths(tmp_folder.name, "function_config.yaml"),
                             create_function_config(self.resources_info))

        init_script_path = self.resources_info.get('lambda').get('init_script')
        # Copy the init script defined by the user to the payload folder
        if init_script_path:
            FileUtils.copy_file(init_script_path,
                                FileUtils.join_paths(tmp_folder.name,
                                                     FileUtils.get_file_name(init_script_path)))

        # Unzip the supervisor file to the temp file
        FileUtils.unzip_folder(supervisor_path, tmp_folder.name)

        # Create dockerfile to generate the new ECR image
        FileUtils.create_file_with_content("%s/Dockerfile" % tmp_folder.name,
                                           self._create_dockerfile_ecr_image(init_script_path))

        # Create the ECR Repo and get the image uri
        ecr_cli = ECR(self.resources_info)
        repo_name = self.function.get('name')
        ecr_image = ecr_cli.get_repository_uri(repo_name)
        if not ecr_image:
            logger.info('Creating ECR repository: %s' % repo_name)
            ecr_image = ecr_cli.create_repository(repo_name)

        # Build the image
        logger.info('Building new ECR image: %s' % ecr_image)
        client.images.build(path=tmp_folder.name, tag=ecr_image, pull=True)

        # Login to the ECR registry
        # TODO: Sometimes it does not work as expected
        registry = ecr_cli.get_registry_url()
        logger.info('Login to ECR registry %s' % registry)
        username, password = ecr_cli.get_authorization_token()
        client.login(username=username, password=password, registry=registry)

        # Push the image, and change it in the container image to use it insteads of the user one
        logger.info('Pushing new image to ECR ...')
        for line in client.images.push(ecr_image, stream=True, decode=True):
            logger.debug(line)
        return "%s:latest" % ecr_image

    @excp.exception(logger)
    def create_function(self):
        # Create tmp folders
        supervisor_path = FileUtils.create_tmp_dir()
        tmp_folder = FileUtils.create_tmp_dir()
        zip_payload_path = None
        if self.function.get('runtime') == "image":
            # Create docker image in ECR
            # Get supervisor with awslambdaric support binary
            asset_name = 'supervisor.zip'
            if self.function.get('container').get('alpine'):
                asset_name = 'supervisor-alpine.zip'
            supervisor_zip_path = SupervisorUtils.download_supervisor_asset(
                self.supervisor_version,
                asset_name,
                supervisor_path.name
            )

            self.function['container']['image'] = self._create_ecr_image(supervisor_zip_path)
        else:
            # Download supervisor
            supervisor_zip_path = SupervisorUtils.download_supervisor(
                self.supervisor_version,
                supervisor_path.name
            )
            # Manage supervisor layer
            self._manage_supervisor_layer(supervisor_zip_path)
            # Create function
            zip_payload_path = FileUtils.join_paths(tmp_folder.name, 'function.zip')
        self._set_image_id()
        self._set_fdl()
        creation_args = self._get_creations_args(zip_payload_path, supervisor_zip_path)
        response = self.client.create_function(**creation_args)
        if response and "FunctionArn" in response:
            self.function['arn'] = response.get('FunctionArn', "")
        return response

    def _set_image_id(self):
        image = self.function.get('container').get('image')
        if image:
            self.function['environment']['Variables']['IMAGE_ID'] = image

    def _set_fdl(self):
        fdl = StrUtils.dict_to_base64_string(create_function_config(self.resources_info))
        self.function['environment']['Variables']['FDL'] = fdl

    def _manage_supervisor_layer(self, supervisor_zip_path: str) -> None:
        layers_client = LambdaLayers(self.resources_info, self.client, supervisor_zip_path)
        self.function.get('layers', []).append(layers_client.get_supervisor_layer_arn())

    @excp.exception(logger)
    def _get_function_code(self, zip_payload_path: str, supervisor_zip_path: str) -> Dict:
        '''Zip all the files and folders needed.'''
        code = {}
        FunctionPackager(self.resources_info, supervisor_zip_path).create_zip(zip_payload_path)
        if self.function.get('deployment').get('bucket', False):
            file_key = f"lambda/{self.function.get('name')}.zip"
            s3_client = S3(self.resources_info)
            s3_client.create_bucket(self.function.get('deployment').get('bucket'))
            s3_client.upload_file(bucket=self.function.get('deployment').get('bucket'),
                                  file_path=zip_payload_path,
                                  file_key=file_key)
            code = {"S3Bucket": self.function.get('deployment').get('bucket'),
                    "S3Key": file_key}
        else:
            code = {"ZipFile": FileUtils.read_file(zip_payload_path, mode="rb")}
        return code

    def delete_function(self):
        function_name = self.resources_info.get('lambda').get('name')
        fdl = self.get_fdl_config(function_name)
        res = self.client.delete_function(function_name)
        runtime = fdl.get('runtime', self.function.get('runtime'))
        if runtime == "image":
            ecr_info = self.resources_info.get('ecr', {'delete_image': True})
            ecr_info.update(fdl.get('ecr', {}))
            # only delete the image if delete_image is True and create_image was True
            if ecr_info.get('delete_image') and fdl.get('container', {}).get('create_image', True):
                self._delete_ecr_image()
        return res

    def link_function_and_bucket(self, bucket_name: str) -> None:
        kwargs = {'FunctionName': self.function.get('name'),
                  'Principal': "s3.amazonaws.com",
                  'SourceArn': f'arn:aws:s3:::{bucket_name}'}
        self.client.add_invocation_permission(**kwargs)

    def preheat_function(self):
        logger.info("Preheating function")
        self._set_request_response_call_parameters()
        self.launch_lambda_instance()
        logger.info("Preheating successful")

    def _launch_async_event(self, s3_event):
        self.set_asynchronous_call_parameters()
        return self._launch_s3_event(s3_event)

    def launch_request_response_event(self, s3_event):
        self._set_request_response_call_parameters()
        return self._launch_s3_event(s3_event)

    def _launch_s3_event(self, s3_event):
        self.function['payload'] = s3_event
        logger.info(f"Sending event for file '{s3_event['Records'][0]['s3']['object']['key']}'")
        return self.launch_lambda_instance()

    def process_asynchronous_lambda_invocations(self, s3_event_list):
        if (len(s3_event_list) > MAX_CONCURRENT_INVOCATIONS):
            for s3_file_chunk in DataTypesUtils.divide_list_in_chunks(s3_event_list, MAX_CONCURRENT_INVOCATIONS):
                self._launch_concurrent_lambda_invocations(s3_file_chunk)
        else:
            self._launch_concurrent_lambda_invocations(s3_event_list)

    def _launch_concurrent_lambda_invocations(self, s3_event_list):
        pool = ThreadPool(processes=len(s3_event_list))
        pool.map(lambda s3_event: self._launch_async_event(s3_event), s3_event_list)
        pool.close()

    def launch_lambda_instance(self):
        if self.is_asynchronous():
            self.set_asynchronous_call_parameters()
        response = self._invoke_lambda_function()
        response_args = {'Response': response,
                         'FunctionName': self.function.get('name'),
                         'IsAsynchronous': self.function.get('asynchronous')}
        return response_args

    def _get_invocation_payload(self):
        # Default payload
        payload = self.function.get('payload', {})
        if not payload:
            # Check for defined run script
            if self.function.get("run_script", False):
                script_path = self.function.get("run_script")
                # We first code to base64 in bytes and then decode those bytes to allow the json lib to parse the data
                # https://stackoverflow.com/questions/37225035/serialize-in-json-a-base64-encoded-data#37239382
                payload = {"script": StrUtils.bytes_to_base64str(FileUtils.read_file(script_path, 'rb'))}
            # Check for defined commands
            # This overrides any other function payload
            if self.function.get("c_args", False):
                payload = {"cmd_args": json.dumps(self.function.get("c_args"))}
        return json.dumps(payload)

    def _invoke_lambda_function(self):
        invoke_args = {'FunctionName':  self.function.get('name'),
                       'InvocationType':  self.function.get('invocation_type'),
                       'LogType':  self.function.get('log_type'),
                       'Payload': self._get_invocation_payload()}
        return self.client.invoke_function(**invoke_args)

    def set_asynchronous_call_parameters(self):
        self.function.update(ASYNCHRONOUS_CALL)

    def _set_request_response_call_parameters(self):
        self.function.update(REQUEST_RESPONSE_CALL)

    def _get_function_environment_variables(self):
        return self.get_function_configuration()['Environment']

    def merge_aws_and_local_configuration(self, aws_conf: Dict) -> Dict:
        result = ConfigFileParser().get_properties().get('aws')
        result['lambda']['name'] = aws_conf['FunctionName']
        result['lambda']['arn'] = aws_conf['FunctionArn']
        result['lambda']['timeout'] = aws_conf['Timeout']
        result['lambda']['memory'] = aws_conf['MemorySize']
        if 'Environment' in result:
            result['lambda']['environment']['Variables'] = aws_conf['Environment']['Variables'].copy()
        if 'Layers' in result:
            result['lambda']['layers'] = aws_conf['Layers'].copy()
        result['lambda']['supervisor']['version'] = aws_conf['SupervisorVersion']
        return result

    def get_all_functions(self, arn_list):
        try:
            return [self.merge_aws_and_local_configuration(self.get_function_configuration(function_arn))
                    for function_arn in arn_list]
        except ClientError as cerr:
            print(f"Error getting function info by arn: {cerr}")

    def get_function_configuration(self, arn: str = None) -> Dict:
        function = arn if arn else self.function.get('name')
        return self.client.get_function_configuration(function)

    def get_fdl_config(self, arn: str = None) -> Dict:
        function = arn if arn else self.function.get('name')
        function_info = self.client.get_function(function)
        # Get the FDL from the env variable
        fdl = function_info.get('Configuration', {}).get('Environment', {}).get('Variables', {}).get('FDL')
        if fdl:
            return yaml.safe_load(StrUtils.decode_base64(fdl))

        # In the future this part can be removed
        if 'Location' in function_info.get('Code'):
            dep_pack_url = function_info.get('Code').get('Location')
        else:
            return {}
        dep_pack = get_file(dep_pack_url)
        # Extract function_config.yaml
        try:
            with ZipFile(io.BytesIO(dep_pack)) as thezip:
                with thezip.open('function_config.yaml') as cfg_yaml:
                    return yaml.safe_load(cfg_yaml)
        except (KeyError, BadZipfile):
            return {}

    @excp.exception(logger)
    def find_function(self, function_name_or_arn=None):
        try:
            # If this call works the function exists
            name_arn = function_name_or_arn if function_name_or_arn else self.function.get('name', '')
            self.get_function_configuration(name_arn)
            return True
        except ClientError as ce:
            # Function not found
            if ce.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:
                raise

    def add_invocation_permission_from_api_gateway(self):
        api = self.resources_info.get('api_gateway')
        # Add Testing permission
        kwargs = {'FunctionName': self.function.get('name'),
                  'Principal': api.get('service_id'),
                  'SourceArn': api.get('source_arn_testing').format(api_region=api.get('region'),
                                                                    account_id=self.resources_info.get('iam').get('account_id'),
                                                                    api_id=api.get('id'))}
        self.client.add_invocation_permission(**kwargs)
        # Add Invocation permission
        kwargs['SourceArn'] = api.get('source_arn_invocation').format(api_region=api.get('region'),
                                                                      account_id=self.resources_info.get('iam').get('account_id'),
                                                                      api_id=api.get('id'),
                                                                      stage_name=api.get('stage_name'))
        self.client.add_invocation_permission(**kwargs)

    def get_api_gateway_id(self):
        env_vars = self._get_function_environment_variables()
        return env_vars['Variables'].get('API_GATEWAY_ID', '')

    def _get_api_gateway_url(self):
        api_id = self.get_api_gateway_id()
        if not api_id:
            raise excp.ApiEndpointNotFoundError(self.function.get('name'))
        return self.resources_info.get('api_gateway').get('endpoint').format(api_id=api_id,
                                                                             api_region=self.resources_info.get('api_gateway').get('region'),
                                                                             stage_name=self.resources_info.get('api_gateway').get('stage_name'))

    def call_http_endpoint(self):
        invoke_args = {'headers': {'X-Amz-Invocation-Type': 'Event'} if self.is_asynchronous() else {}}
        self._set_invoke_args(invoke_args)
        return call_http_endpoint(self._get_api_gateway_url(), **invoke_args)

    def _set_invoke_args(self, invoke_args):
        if self.resources_info.get('api_gateway').get('data_binary', False):
            invoke_args['data'] = self._get_b64encoded_binary_data()
            invoke_args['headers'].update({'Content-Type': 'application/octet-stream'})
        if self.resources_info.get('api_gateway').get('parameters', False):
            invoke_args['params'] = self._parse_http_parameters(self.resources_info.get('api_gateway').get('parameters'))
        if self.resources_info.get('api_gateway').get('json_data', False):
            invoke_args['data'] = self._parse_http_parameters(self.resources_info.get('api_gateway').get('json_data'))
            invoke_args['headers'].update({'Content-Type': 'application/json'})

    def _parse_http_parameters(self, parameters):
        return parameters if type(parameters) is dict else json.loads(parameters)

    @excp.exception(logger)
    def _get_b64encoded_binary_data(self):
        data_path = self.resources_info.get('api_gateway').get('data_binary')
        AWSValidator.validate_http_payload_size(data_path, self.is_asynchronous())
        with open(data_path, 'rb') as data_file:
            return base64.b64encode(data_file.read())

    def wait_function_active(self, function_arn, max_time=60, delay=2):
        func = {"State": "Pending"}
        wait = 0
        while "State" in func and func["State"] == "Pending" and wait < max_time:
            func = self.get_function_configuration(function_arn)
            time.sleep(delay)
            wait += delay
        if func["State"] == "Active":
            return True
        else:
            return False
