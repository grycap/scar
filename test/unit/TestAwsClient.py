import sys
import io
import unittest.mock

from botocore.exceptions import ClientError
from botocore.vendored.requests.exceptions import ReadTimeout
from mock import MagicMock
from scar import AwsClient
from scar import Result
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
            {'Key' : 'input/'}, {'Key' : 'test1'}, {'Key' : 'test2'}, {'Key' : 'test3'}]}
        file_list = AwsClient().get_s3_file_list('test_bucket')
        self.assertEqual(mock_s3_client.call_count, 1)
        self.assertTrue(call().list_objects_v2(Bucket='test_bucket', Prefix='input/') in mock_s3_client.mock_calls)
        self.assertEqual(file_list, ['test1', 'test2', 'test3'])    
        
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
                        
    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_get_function_environment_variables(self, mock_lambda_client):
        mock_lambda_client.return_value.get_function.return_value = {'Configuration' : {'Environment' : 'test'}}
        result = AwsClient().get_function_environment_variables('test')
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().get_function(FunctionName='test') in mock_lambda_client.mock_calls)
        self.assertEqual(result, 'test')

    @unittest.mock.patch('scar.StringUtils.parse_environment_variables')  
    @unittest.mock.patch('scar.AwsClient.get_function_environment_variables')  
    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_update_function_env_variables(self, mock_lambda_client, mock_get_env_vars, mock_string_utils):
        mock_get_env_vars.return_value = "test_env"
        AwsClient().update_function_env_variables('test', 'env_vars')
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().update_function_configuration(Environment='test_env', FunctionName='test') in mock_lambda_client.mock_calls)
        self.assertEqual(mock_string_utils.call_count, 1)
        self.assertTrue(call('env_vars') in mock_string_utils.mock_calls)

    @unittest.mock.patch('scar.AwsClient.get_lambda')        
    def test_update_function_env_variables_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().update_function_env_variables('test1', 'test2')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue('Error updating the environment variables of the lambda function:' in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)
        
    @unittest.mock.patch('scar.AwsClient.get_s3')        
    def test_create_trigger_from_bucket(self, mock_s3_client):
        AwsClient().create_trigger_from_bucket('test_bucket', 'arn:test2')
        self.assertEqual(mock_s3_client.call_count, 1)
        self.assertTrue(call().put_bucket_notification_configuration(Bucket='test_bucket',
                                                                     NotificationConfiguration={'LambdaFunctionConfigurations': [{'LambdaFunctionArn': 'arn:test2', 'Events': ['s3:ObjectCreated:*'], 'Id': 'string', 'Filter': {'Key': {'FilterRules': [{'Value': 'input/', 'Name': 'prefix'}]}}}]}) 
                        in mock_s3_client.mock_calls)

    @unittest.mock.patch('scar.AwsClient.get_s3')        
    def test_create_trigger_from_bucket_error(self, mock_s3_client):
        mock_s3_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().create_trigger_from_bucket('test_bucket', 'arn:test2')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue('Error configuring S3 bucket:' in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)
        
    @unittest.mock.patch('uuid.uuid4')  
    @unittest.mock.patch('scar.Config')      
    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_add_lambda_permissions(self, mock_lambda_client, mock_config, mock_uuid):
        type(mock_config).lambda_name = PropertyMock(return_value='test_name')
        mock_uuid.return_value = 'test_uuid'
        AwsClient().add_lambda_permissions('test_bucket')
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().add_permission(Action='lambda:InvokeFunction', FunctionName='test_name', Principal='s3.amazonaws.com', SourceArn='arn:aws:s3:::test_bucket', StatementId='test_uuid')
                        in mock_lambda_client.mock_calls)

    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_add_lambda_permissions_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().add_lambda_permissions('test_bucket')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue('Error setting lambda permissions:' in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)            
                        
    @unittest.mock.patch('scar.AwsClient.add_s3_bucket_folders')
    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_check_and_create_s3_bucket(self, mock_s3_client, mock_s3_bucket_folders):
        mock_s3_client.return_value.list_buckets.return_value = {'Buckets' : [{'Name' : 'test1'}, {'Name' : 'test_bucket'}]}
        AwsClient().check_and_create_s3_bucket('test_bucket')
        self.assertEqual(mock_s3_bucket_folders.call_count, 1)
        self.assertTrue(call('test_bucket') in mock_s3_bucket_folders.mock_calls)
        
    @unittest.mock.patch('scar.AwsClient.create_s3_bucket')
    @unittest.mock.patch('scar.AwsClient.add_s3_bucket_folders')
    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_check_and_create_s3_bucket_not_found(self, mock_s3_client, mock_s3_bucket_folders, mock_create_s3_bucket):
        mock_s3_client.return_value.list_buckets.return_value = {'Buckets' : []}
        AwsClient().check_and_create_s3_bucket('test_bucket')
        self.assertEqual(mock_s3_bucket_folders.call_count, 1)
        self.assertTrue(call('test_bucket') in mock_s3_bucket_folders.mock_calls)         
        self.assertEqual(mock_create_s3_bucket.call_count, 1)
        self.assertTrue(call('test_bucket') in mock_create_s3_bucket.mock_calls)         

    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_check_and_create_s3_bucket_error(self, mock_s3_client):
        mock_s3_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().check_and_create_s3_bucket('test_bucket')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue('Error getting the S3 buckets list:' in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)            
            
    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_create_s3_bucket(self, mock_s3_client):
        AwsClient().create_s3_bucket('test_bucket')
        self.assertEqual(mock_s3_client.call_count, 1)
        self.assertTrue(call().create_bucket(ACL='private', Bucket='test_bucket') in mock_s3_client.mock_calls)         

    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_create_s3_bucket_error(self, mock_s3_client):
        mock_s3_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().create_s3_bucket('test_bucket')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Error creating the S3 bucket 'test_bucket':" in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)  
        
    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_add_s3_bucket_folders(self, mock_s3_client):
        AwsClient().add_s3_bucket_folders('test_bucket')
        self.assertEqual(mock_s3_client.call_count, 2)
        self.assertTrue(call().put_object(Bucket='test_bucket', Key="input/") in mock_s3_client.mock_calls)
        self.assertTrue(call().put_object(Bucket='test_bucket', Key="output/") in mock_s3_client.mock_calls)         

    @unittest.mock.patch('scar.AwsClient.get_s3')
    def test_add_s3_bucket_folders_error(self, mock_s3_client):
        mock_s3_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().add_s3_bucket_folders('test_bucket')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Error creating the S3 bucket 'test_bucket' folders:" in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)
        
    @unittest.mock.patch('scar.AwsClient.get_user_name')        
    @unittest.mock.patch('scar.AwsClient.get_resource_groups_tagging_api')
    def test_get_functions_arn_list(self, mock_resource_groups_client, mock_get_user_name):
        mock_get_user_name.return_value = 'test_user'
        mock_resource_groups_client.return_value.get_resources.side_effect = [{'ResourceTagMappingList' : [{'ResourceARN' : 'res1'}, {'ResourceARN' : 'res2'}],
                                                                               'PaginationToken' : 'token1'}, 
                                                                              {'ResourceTagMappingList' : [{'ResourceARN' : 'res3'}, {'ResourceARN' : 'res4'}],
                                                                               'PaginationToken' : 'token2'},
                                                                              {'ResourceTagMappingList' : [{'ResourceARN' : 'res5'}, {'ResourceARN' : 'res6'}]}]
        arn_list = AwsClient().get_functions_arn_list()
        self.assertEqual(arn_list, ['res1', 'res2', 'res3', 'res4', 'res5', 'res6'])
        self.assertEqual(mock_resource_groups_client.call_count, 1)
        self.assertTrue(call().get_resources(TagFilters=[{'Key': 'owner', 'Values': ['test_user']}, {'Key': 'createdby', 'Values': ['scar']}], TagsPerPage=100) 
                        in mock_resource_groups_client.mock_calls)
        self.assertTrue(call().get_resources(PaginationToken='token1', TagFilters=[{'Key': 'owner', 'Values': ['test_user']}, {'Key': 'createdby', 'Values': ['scar']}], TagsPerPage=100) 
                        in mock_resource_groups_client.mock_calls)   
        self.assertTrue(call().get_resources(PaginationToken='token2', TagFilters=[{'Key': 'owner', 'Values': ['test_user']}, {'Key': 'createdby', 'Values': ['scar']}], TagsPerPage=100) 
                        in mock_resource_groups_client.mock_calls)            

    @unittest.mock.patch('scar.AwsClient.get_resource_groups_tagging_api')
    def test_get_functions_arn_list_error(self, mock_resource_groups_client):
        mock_resource_groups_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().get_functions_arn_list()
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Error getting function arn by tag:" in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)
        
    @unittest.mock.patch('scar.AwsClient.get_functions_arn_list')        
    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_get_all_functions(self, mock_lambda_client, mock_get_functions_arn_list):
        mock_get_functions_arn_list.return_value = ['res1', 'res2']
        mock_lambda_client.return_value.get_function.side_effect = ['f1', 'f2']
        functions = AwsClient().get_all_functions()
        self.assertEqual(functions, ['f1', 'f2'])
        self.assertEqual(mock_get_functions_arn_list.call_count, 1)
        self.assertEqual(mock_lambda_client.call_count, 2)
        self.assertTrue(call().get_function(FunctionName='res1') in mock_lambda_client.mock_calls)
        self.assertTrue(call().get_function(FunctionName='res2') in mock_lambda_client.mock_calls)            

    @unittest.mock.patch('scar.AwsClient.get_functions_arn_list')    
    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_get_all_functions_error(self, mock_lambda_client, mock_get_functions_arn_list):
        mock_get_functions_arn_list.return_value = ['res1', 'res2']
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().get_all_functions()
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Error getting function info by arn:" in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)        
                     
    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_delete_lambda_function(self, mock_lambda_client):
        mock_lambda_client.return_value.delete_function.return_value = {'ResponseMetadata' : {
                                                                            'RequestId' : 'test_id',
                                                                            'HTTPStatusCode' : 'code_42'
                                                                        },
                                                                        'ExtraData' : 'test_extra'}
        result = Result()
        AwsClient().delete_lambda_function('f1', result)
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().delete_function(FunctionName='f1') in mock_lambda_client.mock_calls)
        self.assertEqual(result.plain_text, "Function 'f1' successfully deleted.\n")
        self.assertEqual(result.json, {'LambdaOutput': {'RequestId': 'test_id', 'HTTPStatusCode': 'code_42'}})
        self.assertEqual(result.verbose, {'LambdaOutput': {'ResponseMetadata' : { 'RequestId' : 'test_id', 'HTTPStatusCode' : 'code_42'},
                                          'ExtraData' : 'test_extra'}})

    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_delete_lambda_function_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().delete_lambda_function('f1', Result())
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Error deleting the lambda function:" in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)   
        
    @unittest.mock.patch('scar.AwsClient.get_log')
    def test_delete_cloudwatch_group(self, mock_log_client):
        mock_log_client.return_value.delete_log_group.return_value = {'ResponseMetadata' : {
                                                                            'RequestId' : 'test_id',
                                                                            'HTTPStatusCode' : 'code_42'
                                                                        },
                                                                        'ExtraData' : 'test_extra'}
        result = Result()
        AwsClient().delete_cloudwatch_group('f1', result)
        self.assertEqual(mock_log_client.call_count, 1)
        self.assertTrue(call().delete_log_group(logGroupName='/aws/lambda/f1') in mock_log_client.mock_calls)
        self.assertEqual(result.plain_text, "Log group 'f1' successfully deleted.\n")
        self.assertEqual(result.json, {'CloudWatchOutput': {'RequestId': 'test_id', 'HTTPStatusCode': 'code_42'}})
        self.assertEqual(result.verbose, {'CloudWatchOutput': {'ResponseMetadata' : { 'RequestId' : 'test_id', 'HTTPStatusCode' : 'code_42'},
                                          'ExtraData' : 'test_extra'}})

    @unittest.mock.patch('scar.AwsClient.get_log')
    def test_delete_cloudwatch_group_warning(self, mock_log_client):
        mock_log_client.side_effect = ClientError({'Error' : {'Code' : 'ResourceNotFoundException', 'Message' : 'test_message'}}, 'test2')
        result = Result()
        AwsClient().delete_cloudwatch_group('f1', result)
        self.assertEqual(result.plain_text, "Warning: Cannot delete log group '/aws/lambda/f1'. Group not found.\n")
        self.assertEqual(result.json, {'Warning': "Cannot delete log group '/aws/lambda/f1'. Group not found."})
        self.assertEqual(result.verbose, {'Warning': "Cannot delete log group '/aws/lambda/f1'. Group not found."})
        
    @unittest.mock.patch('scar.AwsClient.get_log')
    def test_delete_cloudwatch_group_error(self, mock_log_client):
        mock_log_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        AwsClient().delete_cloudwatch_group('f1', Result())
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Error deleting the cloudwatch log:" in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output)                                        

    @unittest.mock.patch('scar.AwsClient.delete_cloudwatch_group')
    @unittest.mock.patch('scar.AwsClient.delete_lambda_function')
    @unittest.mock.patch('scar.AwsClient.check_function_name_not_exists')
    @unittest.mock.patch('scar.Result')
    def test_delete_resources(self, mock_result, mock_function_name, mock_delete_function, mock_delete_group):
        aux_result = Result()
        mock_result.return_value = aux_result
        AwsClient().delete_resources('f1', False, False)
        self.assertEqual(mock_function_name.call_count, 1)
        self.assertTrue(call('f1', False) in mock_function_name.mock_calls)
        self.assertEqual(mock_delete_function.call_count, 1)
        self.assertTrue(call('f1', aux_result) in mock_delete_function.mock_calls)
        self.assertEqual(mock_delete_group.call_count, 1)
        self.assertTrue(call('f1', aux_result) in mock_delete_group.mock_calls)

    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_invoke_function(self, mock_lambda_client):
        mock_lambda_client.return_value.invoke.return_value = 'test_response'
        response = AwsClient().invoke_function('f1', 'test_inv', 'test_log', 'test_payload')
        self.assertEqual(response, 'test_response')
        self.assertEqual(mock_lambda_client.call_count, 1)
        self.assertTrue(call().invoke(FunctionName='f1', InvocationType='test_inv', LogType='test_log', Payload='test_payload')
                        in mock_lambda_client.mock_calls)

    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_invoke_function_client_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ClientError({'Error' : {'Code' : '42', 'Message' : 'test_message'}}, 'test2')
        with self.assertRaises(SystemExit):
            AwsClient().invoke_function('f1', 'test_inv', 'test_log', 'test_payload')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Error invoking lambda function:" in output)
        self.assertTrue('An error occurred (42) when calling the test2 operation: test_message' in output) 

    @unittest.mock.patch('scar.AwsClient.get_lambda')
    def test_invoke_function_read_timeout_error(self, mock_lambda_client):
        mock_lambda_client.side_effect = ReadTimeout()
        with self.assertRaises(SystemExit):
            AwsClient().invoke_function('f1', 'test_inv', 'test_log', 'test_payload')
        output = TestAwsClient.capturedOutput.getvalue()
        self.assertTrue("Timeout reading connection pool:" in output)
                        
if __name__ == '__main__':
    unittest.main()
