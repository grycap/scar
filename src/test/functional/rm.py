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

class RmTest(BaseTest):
            
    def test_rm_function(self):
        self.create_function()
        cmd_out = self.delete_function()
        self.assertEqual(cmd_out, "Function 'scar-func-test' successfully deleted.\nLog group '/aws/lambda/scar-func-test' successfully deleted.\n")        
           
    def test_rm_function_json(self):
        self.create_function()
        cmd = self.scar_bin + ["rm","-n", "scar-func-test", "-j"]
        cmd_out = subprocess.check_output(cmd).decode("utf-8")
        lambda_out,cw_out,_ = cmd_out.split("\n")
        self.assertTrue(json.loads(lambda_out)['LambdaOutput']['HTTPStatusCode'], 204)
        self.assertTrue(json.loads(cw_out)['CloudWatchOutput']['HTTPStatusCode'], 200)
          
    def test_rm_function_verbose(self):
        self.create_function()
        cmd = self.scar_bin + ["rm","-n", "scar-func-test", "-v"]
        cmd_out = subprocess.check_output(cmd).decode("utf-8")
        lambda_out,cw_out,_ = cmd_out.split("\n")
        self.assertTrue(json.loads(lambda_out)['LambdaOutput']['ResponseMetadata']['HTTPStatusCode'], 204)
        self.assertTrue(json.loads(cw_out)['CloudWatchOutput']['ResponseMetadata']['HTTPStatusCode'], 200)
         
    def test_rm_all_functions(self):
        self.create_functions()
        cmd = self.scar_bin + ["rm","-a"]
        subprocess.check_output(cmd).decode("utf-8")
        
    def test_rm_all_functions_json(self):
        self.create_functions()
        cmd = self.scar_bin + ["rm","-a", "-j"]
        subprocess.check_output(cmd).decode("utf-8")
    
    def test_rm_all_functions_verbose(self):
        self.create_functions()
        cmd = self.scar_bin + ["rm","-a", "-v"]
        subprocess.check_output(cmd).decode("utf-8")              

if __name__ == '__main__':
    unittest.main()
    