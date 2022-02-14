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

import os.path
import docker
import scar.logger as logger
from typing import Dict, Set
from scar.providers.aws.ecr import ECR
from scar.utils import FileUtils, SupervisorUtils
from scar.providers.aws.functioncode import create_function_config


class ContainerImage:

    @staticmethod
    def get_asset_name(function_info: Dict) -> str:
        arch = function_info.get('architectures', ['x86_64'])[0]
        arch = '' if arch == 'x86_64' else "-%s" % arch
        alpine = '-alpine' if function_info.get('container').get('alpine') else ''
        return 'supervisor%s%s.zip' % (alpine, arch)

    @staticmethod
    def delete_ecr_image(resources_info: Dict) -> None:
        """Delete the ECR repository created in _create_ecr_image function."""
        ecr_cli = ECR(resources_info)
        repo_name = resources_info.get('lambda').get('name')
        if ecr_cli.get_repository_uri(repo_name):
            logger.info('Deleting ECR repo: %s' % repo_name)
            ecr_cli.delete_repository(repo_name)

    @staticmethod
    def get_supervisor_zip(resources_info: Dict, supervisor_version: str) -> str:
        """Get from cache or download supervisor zip."""
        asset_name = ContainerImage.get_asset_name(resources_info.get('lambda'))
        cached, supervisor_zip_path = SupervisorUtils.is_supervisor_asset_cached(asset_name, supervisor_version)
        if cached:
            # It is cached, do not download again
            logger.debug('Using supervisor asset cached file: ver: %s, asset: %s' % (supervisor_version, asset_name))
            return supervisor_zip_path
        else:
            logger.debug('Downloading supervisor asset file: ver: %s, asset: %s' % (supervisor_version, asset_name))
            return SupervisorUtils.download_supervisor_asset(
                supervisor_version,
                asset_name,
                supervisor_zip_path
            )

    @staticmethod
    def create_ecr_image(resources_info: Dict, supervisor_version: str) -> str:
        """Creates an ECR image using the user provided image adding the supervisor tools."""
        # If the user set an already prepared image return the image name
        image_name = ContainerImage._ecr_image_name_prepared(resources_info.get('lambda').get('container'))
        if image_name:
            return image_name

        tmp_folder = FileUtils.create_tmp_dir()

        # Create function config file
        FileUtils.write_yaml(FileUtils.join_paths(tmp_folder.name, "function_config.yaml"),
                             create_function_config(resources_info))

        init_script_path = resources_info.get('lambda').get('init_script')
        # Copy the init script defined by the user to the payload folder
        if init_script_path:
            FileUtils.copy_file(init_script_path,
                                FileUtils.join_paths(tmp_folder.name,
                                                     FileUtils.get_file_name(init_script_path)))

        # Get supervisor zip
        supervisor_zip_path = ContainerImage.get_supervisor_zip(resources_info, supervisor_version)
        # Unzip the supervisor file to the temp file
        FileUtils.unzip_folder(supervisor_zip_path, tmp_folder.name)

        # Create dockerfile to generate the new ECR image
        FileUtils.create_file_with_content("%s/Dockerfile" % tmp_folder.name,
                                           ContainerImage._create_dockerfile_ecr_image(resources_info.get('lambda')))

        # Create the ECR Repo and get the image uri
        ecr_cli = ECR(resources_info)
        repo_name = resources_info.get('lambda').get('name')
        ecr_image = ecr_cli.get_repository_uri(repo_name)
        if not ecr_image:
            logger.info('Creating ECR repository: %s' % repo_name)
            ecr_image = ecr_cli.create_repository(repo_name)

        # Build and push the image to the ECR repo
        platform = None
        arch = resources_info.get('lambda').get('architectures', ['x86_64'])[0]
        if arch == 'arm64':
            platform = 'linux/arm64'
        return ContainerImage._build_push_ecr_image(tmp_folder.name, ecr_image, platform, ecr_cli.get_authorization_token())

    @staticmethod
    def _create_dockerfile_ecr_image(lambda_info: Dict) -> str:
        """Create dockerfile to generate the new ECR image."""
        dockerfile = 'from %s\n' % lambda_info.get('container').get('image')
        dockerfile += 'ARG FUNCTION_DIR="/var/task"\n'
        dockerfile += 'WORKDIR ${FUNCTION_DIR}\n'
        dockerfile += 'ENV PATH="${FUNCTION_DIR}:${PATH}"\n'
        # Add PYTHONIOENCODING to avoid UnicodeEncodeError as sugested in:
        # https://github.com/aws/aws-lambda-python-runtime-interface-client/issues/19
        dockerfile += 'ENV PYTHONIOENCODING="utf8"\n'

        # Add user environment variables
        vars = lambda_info.get('container').get('environment').get('Variables', {})
        for key, value in vars.items():
            dockerfile += 'ENV %s="%s"\n' % (key, value)

        dockerfile += 'CMD [ "supervisor" ]\n'
        dockerfile += 'ADD supervisor ${FUNCTION_DIR}\n'
        dockerfile += 'COPY function_config.yaml ${FUNCTION_DIR}\n'
        init_script_path = lambda_info.get('init_script')
        if init_script_path:
            dockerfile += 'COPY %s ${FUNCTION_DIR}\n' % FileUtils.get_file_name(init_script_path)
        return dockerfile

    @staticmethod
    def _ecr_image_name_prepared(container_info: Dict) -> str:
        """If the user set an already prepared image return the image name."""
        image_name = container_info.get('image')
        if ":" not in image_name:
            image_name = "%s:latest" % image_name
        if not container_info.get('create_image') and ".dkr.ecr." in image_name:
            logger.info('Image already prepared in ECR.')
            return image_name
        return None

    @staticmethod
    def _build_push_ecr_image(tmp_folder: str, ecr_image: str, platform: str, auth_token: Set) -> str:
        try:
            dclient = docker.from_env()
        except docker.errors.DockerException:
            raise Exception("Error getting docker client. Check if current user has the correct permissions (docker group).")
        logger.info('Building new ECR image: %s' % ecr_image)
        dclient.images.build(path=tmp_folder, tag=ecr_image, pull=True, platform=platform)

        # Login to the ECR registry
        # Known issue it does not work in Widnows WSL environment
        registry = os.path.dirname(ecr_image)
        logger.info('Login to ECR registry %s' % registry)
        dclient.login(username=auth_token[0], password=auth_token[1], registry=registry)

        # Push the image, and change it in the container image to use it insteads of the user one
        logger.info('Pushing new image to ECR ...')
        for line in dclient.images.push(ecr_image, stream=True, decode=True):
            logger.debug(line)
            if 'error' in line:
                raise Exception("Error pushing image: %s" % line['errorDetail']['message'])
        return "%s:latest" % ecr_image