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
"""Module with methods shared by all the classes."""

from typing import Optional, Dict, List, Generator, Union, Any
from distutils import dir_util
import base64
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid
import scar.logger as logger
import scar.http.request as request


class SysUtils:
    """Common methods for system management."""

    @staticmethod
    def is_variable_in_environment(variable: str) -> bool:
        """Checks if a variable is in the system environment."""
        return DataTypesUtils.is_key_in_dict(variable, os.environ)

    @staticmethod
    def set_environment_variable(key: str, variable: Any) -> None:
        """Sets a system environment variable."""
        if key and variable:
            os.environ[key] = variable

    @staticmethod
    def get_environment_variable(variable: str) -> str:
        """Returns the value of system environment variable
        or an empty string if not found."""
        return os.environ.get(variable, '')

    @staticmethod
    def delete_environment_variable(variable: str) -> None:
        """Delete a system environment variable."""
        if SysUtils.is_variable_in_environment(variable):
            del os.environ[variable]

    @staticmethod
    def execute_command_with_msg(command: List[str], cmd_wd: Optional[str] = None,
                                 cli_msg: str = '') -> str:
        """Execute the specified command and return the result."""
        cmd_out = subprocess.check_output(command, cwd=cmd_wd).decode('utf-8')
        logger.debug(cmd_out)
        logger.info(cli_msg)
        return cmd_out[:-1]

    @staticmethod
    def get_filtered_env_vars(key_filter: str) -> Dict:
        """Returns the global variables that start with the
        key_filter provided and removes the filter used."""
        size = len(key_filter)
        env_vars = {}
        for key, val in os.environ.items():
            # Find global variables with the specified prefix
            if key.startswith(key_filter):
                env_vars[key[size:]] = val
        return env_vars


class DataTypesUtils:
    """Common methods for data types management."""

    @staticmethod
    def lazy_property(func):
    # Skipped type hinting: https://github.com/python/mypy/issues/3157
        """ A decorator that makes a property lazy-evaluated."""
        attr_name = '_lazy_' + func.__name__

        @property
        def _lazy_property(self):
            if not hasattr(self, attr_name):
                setattr(self, attr_name, func(self))
            return getattr(self, attr_name)
        return _lazy_property

    @staticmethod
    def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
        """Merge 'dict1' and 'dict2' dicts into 'dict1'.
        'dict2' has precedence over 'dict1'."""
        for key, val in dict2.items():
            if val:
                if key not in dict1:
                    dict1[key] = val
                elif isinstance(val, dict):
                    dict1[key] = DataTypesUtils.merge_dicts(dict1[key], val)
                elif isinstance(val, list):
                    dict1[key] += val
        return dict1

    # is_value_in_dict
    @staticmethod
    def is_key_in_dict(key: str, dictionary: Dict) -> bool:
        """Checks if a key is in the given dictionary."""
        return key in dictionary and dictionary[key]

    @staticmethod
    def divide_list_in_chunks(elements: List, chunk_size: int) -> Generator[List, None, None]:
        """Yield successive n-sized chunks from th elements list."""
        if not elements:
            yield []
        for i in range(0, len(elements), chunk_size):
            yield elements[i:i + chunk_size]

    @staticmethod
    def parse_arg_list(arg_keys: List, cmd_args: Dict) -> Dict:
        """Parse an argument dictionary filtering by the names
        specified in a list."""
        result = {}
        for key in arg_keys:
            if isinstance(key, tuple):
                if key[0] in cmd_args and cmd_args[key[0]]:
                    result[key[1]] = cmd_args[key[0]]
            else:
                if key in cmd_args and cmd_args[key]:
                    result[key] = cmd_args[key]
        return result


class FileUtils:
    """Common methods for file and directory management."""

    @staticmethod
    def copy_file(source: str, dest: str) -> None:
        """Copy file to specified destination."""
        shutil.copy(source, dest)

    @staticmethod
    def copy_dir(source: str, dest: str) -> None:
        """Copy directory to specified destination."""
        dir_util.copy_tree(source, dest)

    @staticmethod
    def get_scar_root_path() -> str:
        """Returns the root path of the project."""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def join_paths(*paths: str) -> str:
        """Returns the strings passed joined as a system path."""
        return os.path.join(*paths)

    @staticmethod
    def get_tmp_dir() -> str:
        """Gets the directory where the temporal
        folder of the system is located."""
        return tempfile.gettempdir()

    @staticmethod
    def create_tmp_dir() -> tempfile.TemporaryDirectory:
        """Creates a directory in the temporal folder of the system.
        When the context is finished, the folder is automatically deleted."""
        return tempfile.TemporaryDirectory()

    @staticmethod
    def get_tree_size(path: str) -> int:
        """Return total size of files in given path and subdirs."""
        total = 0
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                total += FileUtils.get_tree_size(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
        return total

    @staticmethod
    def get_all_files_in_directory(dir_path: str) -> List[str]:
        """Returns a list with all the file paths in
        the specified directory and subdirectories."""
        files = []
        for dirname, _, filenames in os.walk(dir_path):
            for filename in filenames:
                files.append(os.path.join(dirname, filename))
        return files

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Returns the file size in bytes"""
        return os.stat(file_path).st_size

    @staticmethod
    def create_folder(folder_name: str) -> None:
        """Creates a system folder.
        Does nothing if the folder exists."""
        if not os.path.isdir(folder_name):
            os.makedirs(folder_name, exist_ok=True)

    @staticmethod
    def create_file_with_content(path: str, content: Optional[str, bytes]) -> None:
        """Creates a new file with the passed content.
        If the content is a dictionary, first is converted to a string."""
        with open(path, 'w') as fwc:
            fwc.write(content)

    @staticmethod
    def read_file(file_path: str, mode: str = 'r') -> Optional[str, bytes]:
        """Reads the whole specified file and returns the content."""
        with open(file_path, mode) as content_file:
            return content_file.read()

    @staticmethod
    def delete_file(path: str) -> None:
        """Delete the specified file."""
        if os.path.isfile(path):
            os.remove(path)

    @staticmethod
    def delete_folder(path: str) -> None:
        """Delete a folder with all its contents."""
        shutil.rmtree(path)

    @staticmethod
    def create_tar_gz(files_to_archive: List[str], destination_tar_path: str) -> str:
        """Create a .tar.gz file with the passed list of files."""
        with tarfile.open(destination_tar_path, 'w:gz') as tar:
            for file_path in files_to_archive:
                tar.add(file_path, arcname=os.path.basename(file_path))
        return destination_tar_path

    @staticmethod
    def extract_tar_gz(tar_path: str, destination_path: str) -> None:
        """Extract the content of a .tar.gz file in the specified path."""
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(path=destination_path)

    @staticmethod
    def unzip_folder(zip_path: str, folder_where_unzip_path: str) -> None:
        """Must use the unzip binary to preserve the file properties and the symlinks."""
        zip_exe = '/usr/bin/unzip'
        SysUtils.execute_command_with_msg([zip_exe, zip_path],
                                          cmd_wd=folder_where_unzip_path,
                                          cli_msg='Creating function package')    

    @staticmethod
    def zip_folder(zip_path: str, folder_to_zip_path: str, msg: str = '') -> None:
        """Must use the zip binary to preserve the file properties and the symlinks."""
        zip_exe = '/usr/bin/zip'
        SysUtils.execute_command_with_msg([zip_exe, '-r9y', zip_path, '.'],
                                          cmd_wd=folder_to_zip_path,
                                          cli_msg=msg)


class StrUtils:
    """Common methods for string management."""

    @staticmethod
    def decode_base64(value: Union[bytes, str]) -> bytes:
        """Decode a Base64 encoded bytes-like object or
        ASCII string and return the decoded bytes"""
        return base64.b64decode(value)

    @staticmethod
    def encode_base64(value: bytes) -> bytes:
        """Encode a bytes-like object using Base64
        and return the encoded bytes."""
        return base64.b64encode(value)

    @staticmethod
    def base64_to_utf8_string(value: Union[bytes, str]) -> str:
        """Decode a Base64 encoded bytes-like object or ASCII
        string and return the decoded value as a string."""
        return StrUtils.decode_base64(value).decode('utf-8')

    @staticmethod
    def utf8_to_base64_string(value: str) -> str:
        """Encode a 'utf-8' string using Base64 and return
        the encoded value as a string."""
        return StrUtils.encode_base64(bytes(value, 'utf-8')).decode('utf-8')

    @staticmethod
    def dict_to_base64_string(value: Dict) -> str:
        """Encodes a dictionary to base64 and returns a string."""
        return StrUtils.utf8_to_base64_string(json.dumps(value))

    @staticmethod
    def find_expression(string_to_search: str, rgx_pattern: str) -> Optional[str]:
        """Returns the first group that matches the rgx_pattern in the string_to_search."""
        if string_to_search:
            pattern = re.compile(rgx_pattern)
            match = pattern.search(string_to_search)
            if match:
                return match.group()
        return None

    @staticmethod
    def get_random_uuid4_str() -> str:
        """Returns a random generated uuid4 string."""
        return str(uuid.uuid4())


class GitHubUtils:
    """Common methods for GitHub API Queries.
    https://developer.github.com/v3/repos/releases/"""

    @staticmethod
    def get_latest_release(user: str, project: str) -> Optional[str]:
        """Get the tag of the latest release in a repository."""
        url = f'https://api.github.com/repos/{user}/{project}/releases/latest'
        response = json.loads(request.get_file(url))
        if DataTypesUtils.is_key_in_dict('tag_name', response):
            return response['tag_name']
        return None

    @staticmethod
    def exists_release_in_repo(user: str, project: str, tag_name: str) -> bool:
        """Check if a tagged release exists in a repository."""
        url = f'https://api.github.com/repos/{user}/{project}/releases'
        response = json.loads(request.get_file(url))
        if response and response is list:
            for release in response:
                if release['tag_name'] == tag_name:
                    return True
        return False

    @staticmethod
    def get_asset_url(user: str, project: str, asset_name: str,
                      tag_name: str = 'latest') -> Optional[str]:
        """Get the download asset url from the specified github tagged project."""
        if tag_name == 'latest':
            url = f'https://api.github.com/repos/{user}/{project}/releases/latest'
        else:
            if GitHubUtils.exists_release_in_repo(user, project, tag_name):
                url = f'https://api.github.com/repos/{user}/{project}/releases/tags/{tag_name}'
            else:
                return None
        response = json.loads(request.get_file(url))
        if isinstance(response, dict) and 'assets' in response:
            for asset in response['assets']:
                if asset['name'] == asset_name:
                    return asset['browser_download_url']
        return None
