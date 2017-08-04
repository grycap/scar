import os
from unittest.mock import call
import unittest.mock
import sys
from scar import Config

sys.path.append(".")
sys.path.append("..")

class TestConfig(unittest.TestCase):

    filename = "./scar.cfg"
    config = Config()

    def read_config_file(self):
        TestConfig.config.config_parser.read(TestConfig.filename)

    def setUp(self):
        """ Setting up for the test """
        with self.assertRaises(SystemExit):
            TestConfig.config.create_config_file(".")
        self.assertTrue(os.path.isfile(TestConfig.filename))        

    def tearDown(self):
        """Cleaning up after the test"""
        os.remove(TestConfig.filename)                 
        
    def test_create_config_file(self):
        self.read_config_file()
        self.assertEqual(TestConfig.config.config_parser.sections(), ['scar'])
        self.assertEqual(TestConfig.config.config_parser['scar']['lambda_time'], "300")
        self.assertEqual(TestConfig.config.config_parser['scar']['lambda_memory'], "128")
        self.assertEqual(TestConfig.config.config_parser['scar']['lambda_region'], "us-east-1")
        self.assertEqual(TestConfig.config.config_parser['scar']['lambda_timeout_threshold'], "10")
        self.assertEqual(TestConfig.config.config_parser['scar']['lambda_role'], "")
        self.assertEqual(TestConfig.config.config_parser['scar']['lambda_description'], "Automatically generated lambda function")
        
    @unittest.mock.patch('scar.Config.create_config_file')
    @unittest.mock.patch('os.makedirs')
    @unittest.mock.patch('os.path.isdir')
    @unittest.mock.patch('os.path.expanduser')     
    def test_check_config_file_isnotdir(self, mock_expanduser, mock_isdir, mock_makedirs, mock_create_config_file):
        mock_expanduser.return_value = "."
        mock_isdir.return_value = False
        Config().check_config_file()
        self.assertEqual(mock_makedirs.call_count, 1)
        self.assertEqual(mock_create_config_file.call_count, 1)
        self.assertEqual(mock_makedirs.call_args, call('./.scar'))
        self.assertEqual(mock_create_config_file.call_args, call('./.scar'))
        
    @unittest.mock.patch('scar.Config.create_config_file')
    @unittest.mock.patch('os.path.isfile')
    @unittest.mock.patch('os.path.isdir')
    @unittest.mock.patch('os.path.expanduser')     
    def test_check_config_file_isdir_isnotfile(self, mock_expanduser, mock_isdir, mock_isfile, mock_create_config_file):
        mock_expanduser.return_value = "."
        mock_isdir.return_value = True
        mock_isfile.return_value = False
        Config().check_config_file()
        self.assertEqual(mock_create_config_file.call_count, 1)
        self.assertEqual(mock_create_config_file.call_args, call('./.scar'))
        
    @unittest.mock.patch('scar.Config.config_parser.read')
    @unittest.mock.patch('scar.Config.parse_config_file_values')
    @unittest.mock.patch('os.path.isfile')
    @unittest.mock.patch('os.path.isdir')
    @unittest.mock.patch('os.path.expanduser')     
    def test_check_config_file_isdir_isfile(self, mock_expanduser, mock_isdir, mock_isfile, mock_config_file_values, mock_config_parser_read):
        mock_expanduser.return_value = "."
        mock_isdir.return_value = True
        mock_isfile.return_value = True
        mock_config_file_values.return_value = ""
        Config().check_config_file()
        self.assertEqual(mock_config_file_values.call_count, 1)
        self.assertEqual(mock_config_parser_read.call_count, 1)
        self.assertEqual(mock_config_parser_read.call_args, call('./.scar/scar.cfg'))
         
    def test_parse_config_file_values_no_role(self):
        self.read_config_file()
        TestConfig.config.config_parser['scar']['lambda_role'] = ""
        with self.assertRaises(SystemExit):
            TestConfig.config.parse_config_file_values()
        
    def test_parse_config_file_values_with_role(self):
        self.read_config_file()
        TestConfig.config.config_parser['scar']['lambda_role'] = "some role"
        TestConfig.config.parse_config_file_values()
        self.assertEqual(TestConfig.config.lambda_time, 300)
        self.assertEqual(TestConfig.config.lambda_memory, 128)
        self.assertEqual(TestConfig.config.lambda_region, "us-east-1")
        self.assertEqual(TestConfig.config.lambda_timeout_threshold, "10")
        self.assertEqual(TestConfig.config.lambda_role, "some role")
        self.assertEqual(TestConfig.config.lambda_description, "Automatically generated lambda function")             

if __name__ == '__main__':
    unittest.main()
