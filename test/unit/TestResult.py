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

class TestResult(unittest.TestCase):
    
    capturedOutput = None
    result = None

    def setUp(self):
        TestResult.result = Result()
        TestResult.capturedOutput = io.StringIO()
        sys.stdout = TestResult.capturedOutput        

    def tearDown(self):
        TestResult.capturedOutput.close()
        sys.stdout = sys.__stdout__                    
        
    def test_append_to_verbose(self):
        TestResult.result.append_to_verbose("test_key", "test_value")
        self.assertEqual(TestResult.result.verbose, {"test_key" : "test_value"})
        TestResult.result.append_to_verbose("test_key2", "test_value2")
        self.assertEqual(TestResult.result.verbose, {"test_key" : "test_value", "test_key2" : "test_value2"})
        
    def test_append_to_json(self):
        TestResult.result.append_to_json("test_key", "test_value")
        self.assertEqual(TestResult.result.json, {"test_key" : "test_value"})
        TestResult.result.append_to_json("test_key2", "test_value2")
        self.assertEqual(TestResult.result.json, {"test_key" : "test_value", "test_key2" : "test_value2"})
        
    def test_append_to_plain_text(self):
        TestResult.result.append_to_plain_text("test_plain_text")
        self.assertEqual(TestResult.result.plain_text, "test_plain_text\n")
        TestResult.result.append_to_plain_text("test_plain_text2")
        self.assertEqual(TestResult.result.plain_text, "test_plain_text\ntest_plain_text2\n") 
        
    def test_print_verbose_result(self):
        TestResult.result.append_to_verbose("test_key", "test_value")
        TestResult.result.append_to_verbose("test_key2", "test_value2")
        TestResult.result.print_verbose_result()
        output = TestResult.capturedOutput.getvalue()
        self.assertTrue('"test_key": "test_value"' in output)
        self.assertTrue('"test_key2": "test_value2"' in output)

    def test_print_json_result(self):
        TestResult.result.append_to_json("test_key", "test_value")
        TestResult.result.append_to_json("test_key2", "test_value2")
        TestResult.result.print_json_result()
        output = TestResult.capturedOutput.getvalue()
        self.assertTrue('"test_key": "test_value"' in output)
        self.assertTrue('"test_key2": "test_value2"' in output)
        
    def test_print_plain_text_result(self):
        TestResult.result.append_to_plain_text("test_plain_text")
        TestResult.result.append_to_plain_text("test_plain_text2")
        TestResult.result.print_plain_text_result()
        output = TestResult.capturedOutput.getvalue()
        self.assertEquals(output, "test_plain_text\ntest_plain_text2\n\n")
    
    @unittest.mock.patch('scar.Result.print_verbose_result')        
    def test_print_results_verbose(self, mock_verbose):
        TestResult.result.print_results(verbose=True)
        self.assertEqual(mock_verbose.call_count, 1)
        self.assertTrue(call() in mock_verbose.mock_calls)
        
    @unittest.mock.patch('scar.Result.print_json_result')    
    def test_print_results_json(self, mock_json):
        TestResult.result.print_results(json=True)
        self.assertEqual(mock_json.call_count, 1)
        self.assertTrue(call() in mock_json.mock_calls)
        
    @unittest.mock.patch('scar.Result.print_plain_text_result')
    def test_print_results_plain_text(self, mock_plain_text):
        TestResult.result.print_results()
        self.assertEqual(mock_plain_text.call_count, 1)
        self.assertTrue(call() in mock_plain_text.mock_calls)
    
    def test_generate_table(self):
        functions_info = [{'Name':'f1', 'Memory':"256", "Timeout":"300", "Image_id":"test1"},
                          {'Name':'f2', 'Memory':"128", "Timeout":"100", "Image_id":"test2"},
                          {'Name':'f3', 'Memory':"512", "Timeout":"200", "Image_id":"test3"}]
        TestResult.result.generate_table(functions_info)
        output = TestResult.capturedOutput.getvalue()
        result_table = "NAME      MEMORY    TIME  IMAGE_ID\n"
        result_table += "------  --------  ------  ----------\n"
        result_table += "f1           256     300  test1\n"
        result_table += "f2           128     100  test2\n"
        result_table += "f3           512     200  test3\n"
        self.assertEqual(output, result_table)
    
    @unittest.mock.patch('scar.Result.append_to_plain_text') 
    @unittest.mock.patch('scar.Result.append_to_json')     
    @unittest.mock.patch('scar.Result.append_to_verbose')        
    def test_add_warning_message_verbose(self, mock_verbose, mock_json, mock_plain_text):
        TestResult.result.add_warning_message("test_warning")
        self.assertEqual(mock_verbose.call_count, 1)
        self.assertTrue(call('Warning', 'test_warning') in mock_verbose.mock_calls)
        self.assertEqual(mock_json.call_count, 1)
        self.assertTrue(call('Warning', 'test_warning') in mock_json.mock_calls)
        self.assertEqual(mock_plain_text.call_count, 1)
        self.assertTrue(call('Warning: test_warning') in mock_plain_text.mock_calls)                
                        
if __name__ == '__main__':
    unittest.main()
