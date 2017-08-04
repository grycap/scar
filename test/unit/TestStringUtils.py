import base64
import unittest.mock
import scar
import sys
from unittest.mock import MagicMock

sys.path.append(".")
sys.path.append("..")

class TestStringUtils(unittest.TestCase):
        
    @unittest.mock.patch('scar.AwsClient.find_function_name')        
    def test_create_image_based_name(self, mock_find_function_name):
        mock_find_function_name.side_effect = [False, False, True, False, False]
        result = scar.StringUtils().create_image_based_name("")
        self.assertEqual(result, "scar-")
        result = scar.StringUtils().create_image_based_name("test")
        self.assertEqual(result, "scar-test")
        result = scar.StringUtils().create_image_based_name("test")
        self.assertEqual(result, "scar-test-1")
        result = scar.StringUtils().create_image_based_name("grycap/ubuntu:16.04")
        self.assertEqual(result, "scar-grycap-ubuntu-16-04") 

    def test_validate_function_name(self):
        result = scar.StringUtils().validate_function_name("")
        self.assertEqual(result, None)
        result = scar.StringUtils().validate_function_name("scar-test")
        self.assertTrue(result)
        result = scar.StringUtils().validate_function_name("sc.ar")
        self.assertFalse(result)
        
    def test_find_expression(self):
        result = scar.StringUtils().find_expression("","")
        self.assertEqual(result, "")
        result = scar.StringUtils().find_expression("","scar-test")
        self.assertEqual(result, "")
        result = scar.StringUtils().find_expression("scar","scar-test")
        self.assertEqual(result, "scar")
        result = scar.StringUtils().find_expression("ub.*","scar-test-ubuntu-16-04")
        self.assertEqual(result, "ubuntu-16-04")
        result = scar.StringUtils().find_expression("cen.*","scar-test-ubuntu-16-04")
        self.assertEqual(result, None)
        
    def test_base64_to_utf8(self):
        aux = base64.b64encode('test'.encode('utf-8'))
        result = scar.StringUtils().base64_to_utf8(aux)
        self.assertTrue(result == "test")

    def test_escape_list(self):
        test = ["echo", "'hello world'"]
        result = scar.StringUtils().escape_list(test)
        aux = str(test).replace("'", "\"")
        self.assertEqual(result, aux)

    def test_escape_string(self):
        result = scar.StringUtils().escape_string("")
        self.assertEqual(result, "")
        result = scar.StringUtils().escape_string('\\\n"\/')
        self.assertEqual(result, '\\/\\n\\"\\//')        
        result = scar.StringUtils().escape_string('\b\f\r\t')
        self.assertEqual(result, '\\b\\f\\r\\t')

    def test_parse_payload(self):
        attrs = {'read.return_value' : 'test1\\n test2\\n test3'.encode('utf-8')}
        aux = { 'Payload' : MagicMock(**attrs) }
        scar.StringUtils().parse_payload(aux)
        self.assertEqual(aux['Payload'], "est1\n test2\n test")

    def test_parse_base64_response_values(self):
        aux = {'LogResult' : base64.b64encode('test1'.encode('utf-8')),
               'ResponseMetadata' : {
                   'HTTPHeaders' : {
                       'x-amz-log-result' : base64.b64encode('test2'.encode('utf-8'))}}}
        scar.StringUtils().parse_base64_response_values(aux)
        self.assertEqual(aux['LogResult'], 'test1')
        self.assertEqual(aux['ResponseMetadata']['HTTPHeaders']['x-amz-log-result'], 'test2')
        
    def test_parse_log_ids(self):
        aux = { "Payload" : "\nLorem ipsum dolor sit amet\n Suspendisse a mollis diam."}
        scar.StringUtils().parse_log_ids(aux)
        self.assertEqual(aux['LogGroupName'], 'amet')
        self.assertEqual(aux['LogStreamName'], 'iam.')
        
    def test_parse_environment_variables(self):
        config = scar.Config()
        scar.StringUtils().parse_environment_variables(["VAR1=VAL1","VAR2=VAL2","VAR3=VAL3"])
        aux = {"Variables" : {"UDOCKER_DIR":"/tmp/home/.udocker",
                        "UDOCKER_TARBALL":"/var/task/udocker-1.1.0-RC2.tar.gz",
                        "CONT_VAR_VAR1":"VAL1",
                        "CONT_VAR_VAR2":"VAL2",
                        "CONT_VAR_VAR3":"VAL3"}}
        self.assertEqual(config.lambda_env_variables, aux)
        

if __name__ == '__main__':
    unittest.main()