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
from mock import MagicMock
from mock import patch

sys.path.append("..")
sys.path.append(".")

from scar.scarcli import main


class TestSCARCli(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

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
