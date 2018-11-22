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

import json
import os
import subprocess
import unittest

class AwsTest(unittest.TestCase):
    
    scar_base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    scar_bin = ["python3", scar_base_path + "/scar.py"]
    
    def tearDown(self):
        self.execute_command(self.get_cmd(["rm","-a"]))
    
    def execute_command(self, cmd):
        return subprocess.check_output(cmd).decode("utf-8")
    
    def get_cmd(self, extra_args):
        return self.scar_bin + extra_args
    
    def create_function(self, function_name):
        cmd = self.get_cmd(["init","-n", function_name, "-i", "centos:7"])
        cmd_out = self.execute_command(cmd)
        self.assertTrue("Packing udocker files" in cmd_out)
        self.assertTrue("Creating function package" in cmd_out)
        self.assertTrue("Function '{0}' successfully created".format(function_name) in cmd_out)
        self.assertTrue("Log group '/aws/lambda/{0}' successfully created".format(function_name) in cmd_out)
     
    def test_empty_ls_table(self):
        cmd = self.get_cmd(["ls"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(cmd_out, 'NAME    MEMORY    TIME    IMAGE_ID    API_URL\n------  --------  ------  ----------  ---------\n')
          
        cmd = self.get_cmd(["ls", "-j"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(json.loads(cmd_out), {"Functions": []})
          
        cmd = self.get_cmd(["ls", "-v"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(json.loads(cmd_out), {"Functions": []})                 
                  
    def test_init_ls_run_rm_function(self):
        func_name = "scar-test-init-ls-run-rm"
        self.create_function(func_name)
         
        cmd = self.get_cmd(["ls"])
        cmd_out = self.execute_command(cmd)
        self.assertTrue("NAME                        MEMORY    TIME  IMAGE_ID    API_URL" in cmd_out)
        self.assertTrue("------------------------  --------  ------  ----------  ---------" in cmd_out)
        self.assertTrue("{0}       512     300  centos:7    -".format(func_name) in cmd_out)        
        
        cmd = self.get_cmd(["run", "-n", func_name])
        cmd_out = self.execute_command(cmd)
        self.assertTrue("Request Id:" in cmd_out)
        self.assertTrue("Log Group Name: /aws/lambda/{0}".format(func_name) in cmd_out)
        self.assertTrue("Log Stream Name:" in cmd_out)
                 
        cmd = self.get_cmd(["rm","-n", func_name])
        cmd_out = self.execute_command(cmd)
        self.assertTrue("Log group '/aws/lambda/{0}' successfully deleted".format(func_name) in cmd_out)
        self.assertTrue("Function '{0}' successfully deleted".format(func_name) in cmd_out)
         
    def test_init_ls_rm_function_json(self):
        func_name = "scar-test-init-ls-rm-json"
        self.create_function(func_name)
        
        cmd = self.get_cmd(["ls", "-j"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(json.loads(cmd_out),
                         {"Functions": [{"Name": func_name,
                                         "Memory": 512,
                                         "Timeout": 300,
                                         "Image_id": "centos:7",
                                         "Api_gateway": "-"}]
                         })
          
        cmd = self.get_cmd(["rm","-n", func_name, "-j"])
        cmd_out = self.execute_command(cmd)
        cw_out, lambda_out, _ = cmd_out.split("\n")
        self.assertTrue(json.loads(cw_out)['CloudWatchOutput']['HTTPStatusCode'], 200)
        self.assertTrue(json.loads(lambda_out)['LambdaOutput']['HTTPStatusCode'], 204)
         
    def test_init_ls_rm_simple_function_verbose(self):
        func_name = "scar-test-init-ls-rm-verbose"
        self.create_function(func_name)
        cmd = self.scar_bin + ["ls", "-v"]
        cmd_out = self.execute_command(cmd)
        output = json.loads(cmd_out)
        self.assertTrue(output['Functions'][0]['FunctionName'], "scar-func-test")
        self.assertTrue(output['Functions'][0]['Handler'], "scar-func-test.lambda_handler")

        cmd = self.scar_bin + ["rm","-n", func_name, "-v"]
        cmd_out = self.execute_command(cmd)
        cw_out,lambda_out,_ = cmd_out.split("\n")
        self.assertTrue(json.loads(cw_out)['CloudWatchOutput']['ResponseMetadata']['HTTPStatusCode'], 200)
        self.assertTrue(json.loads(lambda_out)['LambdaOutput']['ResponseMetadata']['HTTPStatusCode'], 204)
        
    def test_init_ls_rm_several_functions(self):
        function_names = ["scar-test-init-ls-rm-mult", "scar-test-init-ls-rm-mult-1", "scar-test-init-ls-rm-mult-2"]
        for function_name in function_names:
            self.create_function(function_name)

        cmd = self.get_cmd(["ls"])
        cmd_out = self.execute_command(cmd)
        self.assertTrue("NAME                           MEMORY    TIME  IMAGE_ID    API_URL" in cmd_out)
        self.assertTrue("---------------------------  --------  ------  ----------  ---------" in cmd_out)
        self.assertTrue("{0}         512     300  centos:7    -".format(function_names[0]) in cmd_out)
        self.assertTrue("{0}       512     300  centos:7    -".format(function_names[1]) in cmd_out)
        self.assertTrue("{0}       512     300  centos:7    -".format(function_names[2]) in cmd_out)

        cmd = self.get_cmd(["rm","-a"])
        cmd_out = self.execute_command(cmd)
        for function_name in function_names:
            self.assertTrue("Log group '/aws/lambda/{0}' successfully deleted".format(function_name) in cmd_out)
            self.assertTrue("Function '{0}' successfully deleted".format(function_name) in cmd_out)

if __name__ == '__main__':
    unittest.main()
    