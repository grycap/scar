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
from scar.parser.fdl import FDLParser


class Test(unittest.TestCase):

    def testFDL(self):
        ''' Expected return value (except random ids):
        [{'env_vars':{
            'STORAGE_AUTH_MINIO_PASS_TMPXCMCNA9S': 'mpass',
            'STORAGE_AUTH_MINIO_USER_TMPXCMCNA9S': 'muser',
            'STORAGE_PATH_INPUT_TMPOTOWSDYE': 's3-bucket/test1',
            'STORAGE_PATH_INPUT_TMPXCMCNA9S': 'my-bucket/test',
            'STORAGE_PATH_OUTPUT_TMPOTOWSDYE': 's3-bucket/test1-output',
            'STORAGE_PATH_OUTPUT_TMPXCMCNA9S': 'my-bucket/test-output',
            'STORAGE_PATH_SUFIX_TMPOTOWSDYE': 'avi',
            'STORAGE_PATH_SUFIX_TMPXCMCNA9S': 'wav:srt'},
          'name': 'function1'},
         {'env_vars': {
            'STORAGE_AUTH_MINIO_PASS_TMPXCMCNA9S': 'mpass',
            'STORAGE_AUTH_MINIO_USER_TMPXCMCNA9S': 'muser',
            'STORAGE_PATH_INPUT_TMPXCMCNA9S': 'my-bucket2/test',
            'STORAGE_PATH_OUTPUT_TMPXCMCNA9S': 'my-bucket2/test-output',
            'STORAGE_PATH_PREFIX_TMPXCMCNA9S': 'my_file'},
          'name': 'function2'}]
        '''
        result = FDLParser().parse_yaml('fdl.yaml')
        self.assertEqual(len(result), 2)
        for function in result:
            self.assertTrue(('name' in function) and ('env_vars' in function))
            if function['name'] == 'function1':
                self.assertEqual(len(function['env_vars'].items()), 8)
            elif function['name'] == 'function2':
                self.assertEqual(len(function['env_vars'].items()), 5)                


if __name__ == "__main__":
    unittest.main()
