# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) 2011 - GRyCAP - Universitat Politecnica de Valencia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from src.test.functional.base import BaseTest
import subprocess
import unittest
import json

class LsTest(BaseTest):
    
    def setUp(self):
        self.create_function()        

    def tearDown(self):
        self.delete_function()
          
    def test_ls_table(self):
        cmd = self.scar_bin + ["ls"]
        cmd_out = subprocess.check_output(cmd).decode("utf-8")
        self.assertEqual(cmd_out, 'NAME              MEMORY    TIME  IMAGE_ID\n--------------  --------  ------  ----------\nscar-func-test       512     300  centos:7\n')
          
    def test_ls_json(self):
        cmd = self.scar_bin + ["ls", "-j"]
        cmd_out = subprocess.check_output(cmd).decode("utf-8")
        self.assertEqual(json.loads(cmd_out), {"Functions": [{"Timeout": 300, "Image_id": "centos:7", "Name": "scar-func-test", "Memory": 512}]})
          
    def test_ls_verbose(self):
        cmd = self.scar_bin + ["ls", "-v"]
        cmd_out = subprocess.check_output(cmd).decode("utf-8")
        output = json.loads(cmd_out)
        self.assertTrue(output['Functions'][0]['FunctionName'], "scar-func-test")
        self.assertTrue(output['Functions'][0]['Handler'], "scar-func-test.lambda_handler")               

if __name__ == '__main__':
    unittest.main()
    