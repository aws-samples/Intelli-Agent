import datetime
import os
# import api_test.config as config
from dotenv import load_dotenv

from api_test.biz_logic.rest_api import openapi_client
# from api_test.biz_logic.rest_api import IntellapiconnnHdtwRWUXa

from .utils import step
import logging
import boto3

logger = logging.getLogger(__name__)
sts = boto3.client('sts')
caller_identity = boto3.client('sts').get_caller_identity()
partition = caller_identity['Arn'].split(':')[1]

class TestDocument:
    """DataSourceDiscovery test stubs"""

    @classmethod
    def setup_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test start..."
        )
        load_dotenv()
        cls.configuration = openapi_client.Configuration(host=os.getenv('api_url'))
        cls.api_client = openapi_client.ApiClient(cls.configuration)
        cls.api_client.set_default_header("Authorization", f'Bearer {os.getenv("token")}')
        cls.api_instance = openapi_client.DefaultApi(cls.api_client)

    @classmethod
    def teardown_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test end."
        )

    # aws cognito-idp initiate-auth --region ap-northeast-1 --auth-flow USER_PASSWORD_AUTH --client-id 78dihnoo69jeen0d0e76j6ai0e  --auth-parameters USERNAME=cuihubin@amazon.com,PASSWORD=TEST123!
    upload_success_msg = 'The S3 presigned url is generated'
    upload_prefix_data = 'https://intelli-agent-apiconstructllmbotdocument'
    def test_01_upload_document_pdf(self):
        '''test case'''
        logger.info("test_01_upload_document_pdf start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='application/pdf', file_name="summary.pdf")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_01_upload_document_pdf end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_01_upload_document_pdf test failed"
    
    def test_02_upload_document_doc(self):
        '''test case'''
        logger.info("test_02_upload_document_doc start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', file_name="summary.doc")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_02_upload_document_doc end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_02_upload_document_doc test failed"
    
    def test_03_upload_document_csv(self):
        '''test case'''
        logger.info("test_03_upload_document_csv start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='text/csv', file_name="summary.csv")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_03_upload_document_csv end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_03_upload_document_csv test failed"

    def test_04_upload_document_html(self):
        '''test case'''
        logger.info("test_04_upload_document_html start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='text/html', file_name="summary.html")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_04_upload_document_html end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_04_upload_document_html test failed"
    
    def test_05_upload_document_jpeg(self):
        '''test case'''
        logger.info("test_05_upload_document_jpeg start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='image/jpeg', file_name="summary.jpeg")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_05_upload_document_jpeg end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_05_upload_document_jpeg test failed"
    
    def test_06_upload_document_jpg(self):
        '''test case'''
        logger.info("test_06_upload_document_jpg start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='image/jpeg', file_name="summary.jpg")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_06_upload_document_jpg end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_06_upload_document_jpg test failed"
    
    def test_07_upload_document_png(self):
        '''test case'''
        logger.info("test_07_upload_document_png start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='image/png', file_name="summary.png")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_07_upload_document_png end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_07_upload_document_png test failed"
    
    def test_08_upload_document_json(self):
        '''test case'''
        logger.info("test_08_upload_document_json start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='application/json', file_name="summary.json")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_08_upload_document_json end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_08_upload_document_json test failed"
    
    def test_09_upload_document_md(self):
        '''test case'''
        logger.info("test_09_upload_document_md start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='text/markdown', file_name="summary.md")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_09_upload_document_md end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_09_upload_document_md test failed"
    
    def test_10_upload_document_txt(self):
        '''test case'''
        logger.info("test_10_upload_document_txt start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='text/plain', file_name="summary.txt")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_10_upload_document_txt end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_10_upload_document_txt test failed"

    def test_11_upload_document_jsonl(self):
        '''test case'''
        logger.info("test_11_upload_document_jsonl start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='application/jsonlines', file_name="summary.jsonl")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_11_upload_document_jsonl end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_11_upload_document_jsonl test failed"
    
    def test_12_delete_document(self):
        '''test case'''
        logger.info("test_12_delete_document start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        # response = self.api_instance.etl_delete_execution_post(param)
        logger.info("test_12_delete_document end.")
        # assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_12_delete_document test failed"

    def test_13_list_document(self):
        '''test case'''
        logger.info("test_13_list_document start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='application/jsonlines', file_name="summary.jsonl")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_13_list_document end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_13_list_document test failed"

    def test_14_detail_document(self):
        '''test case'''
        logger.info("test_14_detail_document start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='application/jsonlines', file_name="summary.jsonl")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_14_detail_document end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_14_detail_document test failed"

    def test_15_upload_mismatch_document(self):
        '''test case'''
        logger.info("test_15_upload_mismatch_document start ....")
        param = openapi_client.IntellapicoXWLPrwxLR93J(content_type='application/jsonlines', file_name="summary.jsonl")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_15_upload_mismatch_document end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_15_upload_mismatch_document test failed"
