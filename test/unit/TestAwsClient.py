import boto3
import sys
import io
import unittest.mock

from botocore.exceptions import ClientError
from mock import MagicMock
from scar import AwsClient
from unittest.mock import call
from unittest.mock import PropertyMock

sys.path.append(".")
sys.path.append("..")

class TestAwsClient(unittest.TestCase):

    capturedOutput = io.StringIO()

    def setUp(self):
        TestAwsClient.capturedOutput = io.StringIO()
        sys.stdout = TestAwsClient.capturedOutput       

    def tearDown(self):
        TestAwsClient.capturedOutput.close()
        sys.stdout = sys.__stdout__                    
        
    def test_check_memory_error(self):
        with self.assertRaises(Exception) as context:
            AwsClient().check_memory(-10)
        self.assertTrue('Incorrect memory size specified' in str(context.exception))
        with self.assertRaises(Exception) as context:
            AwsClient().check_memory(2000)
        self.assertTrue('Incorrect memory size specified' in str(context.exception))
        
    def test_check_memory(self):
        self.assertEqual(128, AwsClient().check_memory(128))
        self.assertEqual(1536, AwsClient().check_memory(1536))
        self.assertEqual(256, AwsClient().check_memory(237))
                    
    def test_check_time_error(self):
        with self.assertRaises(Exception) as context:
            AwsClient().check_time(0)
        self.assertTrue('Incorrect time specified' in str(context.exception))
        with self.assertRaises(Exception) as context:
            AwsClient().check_time(3000)
        self.assertTrue('Incorrect time specified' in str(context.exception))

    def test_check_time(self):
        self.assertEqual(1, AwsClient().check_time(1))
        self.assertEqual(300, AwsClient().check_time(300))
        self.assertEqual(147, AwsClient().check_time(147))

    @unittest.mock.patch('boto3.client')        
    def test_get_user_name(self, mock_client):
        mock_client.return_value.get_user.return_value = {'User' : { 'UserName' : 'test1' }}
        user = AwsClient().get_user_name()
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('iam', region_name='us-east-1'))       
        self.assertTrue(call().get_user() in mock_client.mock_calls)
        self.assertEqual(user, 'test1')

    @unittest.mock.patch('boto3.client')        
    def test_get_user_name_error(self, mock_client):
        mock_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'user/testu bla'}}, 'test2')
        user = AwsClient().get_user_name()
        self.assertEqual(user, 'testu')

    @unittest.mock.patch('boto3.Session')        
    def test_get_access_key(self, mock_session):
        credentials = MagicMock()
        access_key = PropertyMock(return_value='test')
        mock_session.return_value.get_credentials.return_value = credentials
        type(credentials).access_key = access_key
        access_key = AwsClient().get_access_key()
        self.assertEqual(access_key, 'test')
        
    @unittest.mock.patch('boto3.client')
    def test_get_boto3_client_no_region(self, mock_client):
        AwsClient().get_boto3_client('test')
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('test', region_name='us-east-1'))
        
    @unittest.mock.patch('boto3.client')
    def test_get_boto3_client(self, mock_client):
        AwsClient().get_boto3_client('test', 'test-region')
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('test', region_name='test-region'))

    @unittest.mock.patch('boto3.client')
    def test_get_lambda(self, mock_client):
        AwsClient().get_lambda()
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('lambda', region_name='us-east-1'))

    @unittest.mock.patch('boto3.client')
    def test_get_log(self, mock_client):
        AwsClient().get_log()
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('logs', region_name='us-east-1'))
        
    @unittest.mock.patch('boto3.client')
    def test_get_iam(self, mock_client):
        AwsClient().get_iam()
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('iam', region_name='us-east-1'))

    @unittest.mock.patch('boto3.client')
    def test_get_resource_groups_tagging_api(self, mock_client):
        AwsClient().get_resource_groups_tagging_api()
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('resourcegroupstaggingapi', region_name='us-east-1'))

    @unittest.mock.patch('boto3.client')
    def test_get_s3(self, mock_client):
        AwsClient().get_s3()
        self.assertEqual(mock_client.call_count, 1)
        self.assertEqual(mock_client.call_args, call('s3', region_name='us-east-1'))

    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_get_s3_file_list(self, mock_s3_client): 
        mock_s3_client.return_value.list_objects_v2.return_value = {'Contents' : [
            {'Key' : 'input/'},{'Key' : 'test1'},{'Key' : 'test2'},{'Key' : 'test3'}]}
        file_list = AwsClient().get_s3_file_list('test_bucket')
        self.assertEqual(mock_s3_client.call_count, 1)
        self.assertTrue(call().list_objects_v2(Bucket='test_bucket', Prefix='input/') in mock_s3_client.mock_calls)
        self.assertEqual(file_list, ['test1','test2','test3'])    
        
    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_get_s3_file_list_empty_list(self, mock_s3_client): 
        mock_s3_client.return_value.list_objects_v2.return_value = {'Contents' : []}
        file_list = AwsClient().get_s3_file_list('test_bucket')
        self.assertEqual(mock_s3_client.call_count, 1)
        self.assertTrue(call().list_objects_v2(Bucket='test_bucket', Prefix='input/') in mock_s3_client.mock_calls)
        self.assertEqual(file_list, [])     
        
    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_find_function_name_empty_list(self, mock_lambda_client):
        paginator = MagicMock()
        paginator.paginate.return_value = []
        mock_lambda_client.return_value.get_paginator.return_value = paginator
        result = AwsClient().find_function_name('test')
        self.assertEqual(result, False)
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().get_paginator('list_functions') in mock_lambda_client.mock_calls)
        self.assertTrue(call.paginate() in paginator.mock_calls)
        
    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_find_function_name(self, mock_lambda_client):
        paginator = MagicMock()
        paginator.paginate.return_value = [{'Functions' : [{'FunctionName' : 'test1'}, {'FunctionName' : 'test'}]}]
        mock_lambda_client.return_value.get_paginator.return_value = paginator
        result = AwsClient().find_function_name('test')
        self.assertEqual(result, True)
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().get_paginator('list_functions') in mock_lambda_client.mock_calls)
        self.assertTrue(call.paginate() in paginator.mock_calls)      
        
    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_find_function_name_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        with self.assertRaises(SystemExit):
            AwsClient().find_function_name('test')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue('Error listing the lambda functions:' in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)        

    @unittest.mock.patch('scar.AwsClient.find_function_name')        
    def test_check_function_name_not_exists_no_json(self, mock_find_function_name):
        mock_find_function_name.return_value = False
        with self.assertRaises(SystemExit):
            AwsClient().check_function_name_not_exists('test', False)
        
    @unittest.mock.patch('scar.AwsClient.find_function_name')        
    def test_check_function_name_not_exists_json(self, mock_find_function_name):
        mock_find_function_name.return_value = False
        with self.assertRaises(SystemExit):
            AwsClient().check_function_name_not_exists('test', True)
        
    @unittest.mock.patch('scar.AwsClient.find_function_name')        
    def test_check_function_name_not_exists(self, mock_find_function_name):
        mock_find_function_name.return_value = True
        AwsClient().check_function_name_not_exists('test', True)
        
    @unittest.mock.patch('scar.AwsClient.find_function_name')        
    def test_check_function_name_exists_no_json(self, mock_find_function_name):
        mock_find_function_name.return_value = True
        with self.assertRaises(SystemExit):
            AwsClient().check_function_name_exists('test', False)
        
    @unittest.mock.patch('scar.AwsClient.find_function_name')        
    def test_check_function_name_exists_json(self, mock_find_function_name):
        mock_find_function_name.return_value = True
        with self.assertRaises(SystemExit):
            AwsClient().check_function_name_exists('test', True)
        
    @unittest.mock.patch('scar.AwsClient.find_function_name')        
    def test_check_function_name_exists(self, mock_find_function_name):
        mock_find_function_name.return_value = False
        AwsClient().check_function_name_exists('test', True)     
        
    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_update_function_timeout(self, mock_lambda_client):
        AwsClient().update_function_timeout('test', 125)
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().update_function_configuration(FunctionName='test', Timeout=125) in mock_lambda_client.mock_calls)

    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_update_function_timeout_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().update_function_timeout('test', 125)
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue('Error updating lambda function timeout:' in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)

    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_update_function_memory(self, mock_lambda_client):
        AwsClient().update_function_memory('test', 256)
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().update_function_configuration(FunctionName='test', MemorySize=256) in mock_lambda_client.mock_calls)

    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_update_function_memory_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().update_function_memory('test', 256)
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue('Error updating lambda function memory:' in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)
                        
if __name__ == '__main__':
    unittest.main()