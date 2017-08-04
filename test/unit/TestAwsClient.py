import unittest
import sys

sys.path.append(".")
sys.path.append("..")

from scar import AwsClient

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

if __name__ == '__main__':
    unittest.main()