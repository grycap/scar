#! /usr/bin/python

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
import unittest
import sys
import os
import tempfile
import yaml
import json
from mock import patch

sys.path.append("..")
sys.path.append(".")

from scar.scarcli import main
from scar.parser.cfgfile import ConfigFileParser, _DEFAULT_CFG
from scar.utils import FileUtils


class TestSCARCli(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

    def setUp(self):
        if not FileUtils.is_file(ConfigFileParser.config_file_path):
            FileUtils.create_folder(ConfigFileParser.config_file_folder)
            FileUtils.create_file_with_content(ConfigFileParser.config_file_path,
                                        json.dumps(_DEFAULT_CFG, indent=2))

    @patch('scar.scarcli.AWS')
    @patch('scar.scarcli.OSCAR')
    def test_main(self, oscar, aws):
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
        tmpfile.write(b"functions:\n")
        tmpfile.write(b"  aws:\n")
        tmpfile.write(b"  - lambda:\n")
        tmpfile.write(b"      name: func_name\n")
        tmpfile.close()
        sys.argv = ['scar', 'init', '-f', tmpfile.name]
        main()
        os.unlink(tmpfile.name)
        self.assertEqual(aws.call_args_list[0][0], ('init',))
        self.assertEqual(oscar.call_args_list[0][0], ('init',))
        with open(os.environ['SCAR_TMP_CFG']) as f:
            cfg_file = yaml.safe_load(f.read())
        self.assertEqual(cfg_file["functions"]["aws"][0]["api_gateway"]["boto_profile"], "default")
        os.unlink(os.environ['SCAR_TMP_CFG'])
