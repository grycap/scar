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
    function_names = ["scar-func-test", "scar-func-test-1", "scar-func-test-2"]
    
    def tearDown(self):
        self.execute_command(self.get_cmd(["rm","-a"]))
    
#     group = parser_init.add_mutually_exclusive_group(required=True)
#     group.add_argument("-i", "--image_id", help="Container image id (i.e. centos:7)")
#     group.add_argument("-if", "--image_file", help="Container image file (i.e. centos.tar.gz)")
#     # Set the optional arguments
#     parser_init.add_argument("-d", "--description", help="Lambda function description.")
#     parser_init.add_argument("-db", "--deployment_bucket", help="Bucket where the deployment package is going to be uploaded.")
#     parser_init.add_argument("-e", "--environment_variables", action='append', help="Pass environment variable to the container (VAR=val). Can be defined multiple times.")
#     parser_init.add_argument("-n", "--name", help="Lambda function name")
#     parser_init.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
#     parser_init.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
#     parser_init.add_argument("-tt", "--timeout_threshold", type=int, help="Extra time used to postprocess the data. This time is extracted from the total time of the lambda function.")
#     parser_init.add_argument("-j", "--json", help="Return data in JSON format", action="store_true")
#     parser_init.add_argument("-v", "--verbose", help="Show the complete aws output in json format", action="store_true")
#     parser_init.add_argument("-s", "--script", help="Path to the input file passed to the function")
#     parser_init.add_argument("-es", "--event_source", help="Name specifying the source of the events that will launch the lambda function. Only supporting buckets right now.")
#     parser_init.add_argument("-lr", "--lambda_role", help="Lambda role used in the management of the functions")
#     parser_init.add_argument("-r", "--recursive", help="Launch a recursive lambda function", action="store_true")
#     parser_init.add_argument("-p", "--preheat", help="Preheats the function running it once and downloading the necessary container", action="store_true")
#     parser_init.add_argument("-ep", "--extra_payload", help="Folder containing files that are going to be added to the payload of the lambda function")
                 
    def execute_command(self, cmd):
        return subprocess.check_output(cmd).decode("utf-8")
    
    def get_cmd(self, extra_args):
        return self.scar_bin + extra_args
    
    def create_function(self, function_name):
        cmd = self.get_cmd(["init","-n", function_name, "-i", "centos:7"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(cmd_out, "Creating lambda function.\nFunction '%s' successfully created.\nCreating cloudwatch log group.\nLog group '/aws/lambda/%s' successfully created.\nSetting log group policy.\n" % (function_name,function_name))        
     
    def test_empty_ls_table(self):
        cmd = self.get_cmd(["ls"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(cmd_out, 'NAME    MEMORY    TIME    IMAGE_ID\n------  --------  ------  ----------\n')
          
        cmd = self.get_cmd(["ls", "-j"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(json.loads(cmd_out), {"Functions": []})
          
        cmd = self.get_cmd(["ls", "-v"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(json.loads(cmd_out), {"Functions": []})                 
                  
    def test_init_ls_run_rm_function(self):
        self.create_function(self.function_names[0])
         
        cmd = self.get_cmd(["ls"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(cmd_out, 'NAME              MEMORY    TIME  IMAGE_ID\n--------------  --------  ------  ----------\nscar-func-test       512     300  centos:7\n')
        
        cmd = self.get_cmd(["run", "-n", self.function_names[0]])
        cmd_out = self.execute_command(cmd)
        self.assertTrue("Request Id:" in cmd_out)
        self.assertTrue("Log group name: /aws/lambda/scar-func-test" in cmd_out)
        self.assertTrue("Log stream name:" in cmd_out)
                 
        cmd = self.get_cmd(["rm","-n", self.function_names[0]])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(cmd_out, "Function 'scar-func-test' successfully deleted.\nLog group '/aws/lambda/scar-func-test' successfully deleted.\n")        
         
    def test_init_ls_rm_function_json(self):
        init_cmd = self.get_cmd(["init","-n", self.function_names[0], "-i", "centos:7"])
        create_out = subprocess.check_output(init_cmd).decode("utf-8")
        self.assertEqual(create_out, "Creating lambda function.\nFunction 'scar-func-test' successfully created.\nCreating cloudwatch log group.\nLog group '/aws/lambda/scar-func-test' successfully created.\nSetting log group policy.\n")
          
        cmd = self.get_cmd(["ls", "-j"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(json.loads(cmd_out), {"Functions": [{"Timeout": 300, "Image_id": "centos:7", "Name": "scar-func-test", "Memory": 512}]})
          
        cmd = self.get_cmd(["rm","-n", "scar-func-test", "-j"])
        cmd_out = self.execute_command(cmd)
        lambda_out,cw_out,_ = cmd_out.split("\n")
        self.assertTrue(json.loads(lambda_out)['LambdaOutput']['HTTPStatusCode'], 204)
        self.assertTrue(json.loads(cw_out)['CloudWatchOutput']['HTTPStatusCode'], 200)
         
    def test_init_ls_rm_simple_function_verbose(self):
        init_cmd = self.get_cmd(["init","-n", self.function_names[0], "-i", "centos:7"])
        create_out = subprocess.check_output(init_cmd).decode("utf-8")
        self.assertEqual(create_out, "Creating lambda function.\nFunction 'scar-func-test' successfully created.\nCreating cloudwatch log group.\nLog group '/aws/lambda/scar-func-test' successfully created.\nSetting log group policy.\n")
          
        cmd = self.scar_bin + ["ls", "-v"]
        cmd_out = self.execute_command(cmd)
        output = json.loads(cmd_out)
        self.assertTrue(output['Functions'][0]['FunctionName'], "scar-func-test")
        self.assertTrue(output['Functions'][0]['Handler'], "scar-func-test.lambda_handler")
  
        cmd = self.scar_bin + ["rm","-n", "scar-func-test", "-v"]
        cmd_out = self.execute_command(cmd)
        lambda_out,cw_out,_ = cmd_out.split("\n")
        self.assertTrue(json.loads(lambda_out)['LambdaOutput']['ResponseMetadata']['HTTPStatusCode'], 204)
        self.assertTrue(json.loads(cw_out)['CloudWatchOutput']['ResponseMetadata']['HTTPStatusCode'], 200)      
        
    def test_init_ls_rm_several_functions(self):
        for function_name in self.function_names:
            self.create_function(function_name)
         
        cmd = self.get_cmd(["ls"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(cmd_out, 'NAME                MEMORY    TIME  IMAGE_ID\n----------------  --------  ------  ----------\nscar-func-test         512     300  centos:7\nscar-func-test-1       512     300  centos:7\nscar-func-test-2       512     300  centos:7\n')
                 
        cmd = self.get_cmd(["rm","-a"])
        cmd_out = self.execute_command(cmd)
        self.assertEqual(cmd_out, "Function 'scar-func-test' successfully deleted.\nLog group '/aws/lambda/scar-func-test' successfully deleted.\nFunction 'scar-func-test-1' successfully deleted.\nLog group '/aws/lambda/scar-func-test-1' successfully deleted.\nFunction 'scar-func-test-2' successfully deleted.\nLog group '/aws/lambda/scar-func-test-2' successfully deleted.\n")

if __name__ == '__main__':
    unittest.main()
    