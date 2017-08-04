import unittest.mock
import sys
import boto3
from scar import AwsClient
from unittest.mock import call

sys.path.append(".")
sys.path.append("..")

class TestAwsClient(unittest.TestCase):
        
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

if __name__ == '__main__':
    unittest.main()