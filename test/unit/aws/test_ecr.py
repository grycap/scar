
import unittest
import sys
from mock import MagicMock
from mock import patch, call


sys.path.append("..")
sys.path.append(".")
sys.path.append("../..")

from scar.providers.aws.ecr import ECR

class TestECRC(unittest.TestCase):

    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)


    def test_init(self):
        ecr = ECR({})
        self.assertEqual(type(ecr.client.client).__name__, "ECR")

    @patch('boto3.Session')
    def test_get_authorization_token(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['get_authorization_token'])
        session.client.return_value = client
        boto_session.return_value = session
        ecr = ECR({})
        token = "QVdTOnRva2Vu"
        ecr.client.client.get_authorization_token.return_value = {'authorizationData': [{'authorizationToken': token}]}
        self.assertEqual(ecr.get_authorization_token(), ["AWS", "token"])

    @patch('boto3.Session')
    def test_get_registry_url(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['describe_registry'])
        session.client.return_value = client
        boto_session.return_value = session
        ecr = ECR({})
        ecr.client.client.describe_registry.return_value = {'registryId': 'REG_ID'}
        self.assertEqual(ecr.get_registry_url(), "REG_ID.dkr.ecr.us-east-1.amazonaws.com")

    @patch('boto3.Session')
    def test_get_repository_uri(self, boto_session):
        session = MagicMock(['client'])
        client = MagicMock(['describe_repositories'])
        session.client.return_value = client
        boto_session.return_value = session
        ecr = ECR({})
        ecr.client.client.describe_repositories.return_value = {'repositories': [{'repositoryUri': 'URI'}]}
        self.assertEqual(ecr.get_repository_uri('repo_name'), 'URI')
        self.assertEqual(ecr.client.client.describe_repositories.call_args_list[0], call(repositoryNames=['repo_name']))
