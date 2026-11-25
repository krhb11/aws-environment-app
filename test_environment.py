import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('environment_app',Path(__file__).parent/'index.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)

class EnvironmentTests(unittest.TestCase):
    def test_environment_checks_are_read_only_and_do_not_invoke_models(self):
        calls=[]
        class S3:
            def get_bucket_location(self,**kwargs):calls.append('bucket-location');return {'LocationConstraint':'ap-northeast-2'}
        class Vectors:
            def get_index(self,**kwargs):calls.append('get-index');return {'index':{'indexName':'books','dimension':256,'distanceMetric':'cosine'}}
            def list_vectors(self,**kwargs):calls.append('list-vectors');return {'vectors':[]}
        def client(name):
            if name=='s3':return S3()
            if name=='s3vectors':return Vectors()
            raise AssertionError('Unexpected service access '+name)
        fake=types.SimpleNamespace(client=client)
        env={'WEB_BUCKET':'web','DATA_BUCKET':'data','VECTOR_INDEX_ARN':'test-index','EMBEDDING_MODEL':'embed','GENERATION_MODEL':'generation'}
        with patch.dict(sys.modules,{'boto3':fake}),patch.dict(os.environ,env):
            result=app.handler({'rawPath':'/dev/api/environment','requestContext':{'stage':'dev','http':{'method':'GET'}}},None)
        self.assertEqual(result['statusCode'],200)
        body=json.loads(result['body'])
        self.assertTrue(body['vector_index']['empty'])
        self.assertEqual(body['chatbot'],'not_implemented')
        self.assertEqual(calls,['bucket-location','bucket-location','get-index','list-vectors'])

if __name__=='__main__':unittest.main()
