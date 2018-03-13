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

import os
import unittest
import subprocess

class BaseTest(unittest.TestCase):
    
    scar_base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    scar_bin = ["python3", scar_base_path + "/scar.py"]
    func_names = ["scar-func-test", "scar-func-test-1", "scar-func-test-2"]
    
    def setUp(self):
        print("Executing: ", self._testMethodName)    
    
    def create_function(self):
        cmd = self.scar_bin + ["init","-n", self.func_names[0], "-i", "centos:7"]
        return subprocess.check_output(cmd).decode("utf-8")
        
    def delete_function(self):
        cmd = self.scar_bin + ["rm","-n", self.func_names[0]]
        return subprocess.check_output(cmd).decode("utf-8")
        
    def create_functions(self):
        cmd_out = []
        for func_name in self.func_names:
            cmd = self.scar_bin + ["init","-n", func_name, "-i", "centos:7"]
            cmd_out.append(subprocess.check_output(cmd).decode("utf-8"))
        return cmd_out
        
    def delete_functions(self):
        cmd_out = []
        for func_name in self.func_names:
            cmd = self.scar_bin + ["rm","-n", func_name]
            cmd_out.append(subprocess.check_output(cmd).decode("utf-8"))
        return cmd_out

    
#     def setUp(self):
#         BaseFunctionalTest.capturedOutput = io.StringIO()
#         sys.stdout = BaseFunctionalTest.capturedOutput        
# 
#     def tearDown(self):
#         BaseFunctionalTest.capturedOutput.close()
#         sys.stdout = sys.__stdout__
    