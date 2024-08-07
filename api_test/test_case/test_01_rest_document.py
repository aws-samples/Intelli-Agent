import datetime
import json
import os
# import api_test.config as config
from dotenv import load_dotenv

from api_test.biz_logic.rest_api import openapi_client
# from api_test.biz_logic.rest_api import IntellapiconnnHdtwRWUXa

from .utils import step
import logging
import boto3
from pprint import pprint

logger = logging.getLogger(__name__)
sts = boto3.client('sts')
caller_identity = boto3.client('sts').get_caller_identity()
partition = caller_identity['Arn'].split(':')[1]

class TestDocument:
    """DataSourceDiscovery test stubs"""

    @classmethod
    def setup_class(self):
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test start..."
        )
        load_dotenv()
        self.configuration = openapi_client.Configuration(host=os.getenv('api_url'))
        self.api_client = openapi_client.ApiClient(self.configuration)
        self.api_client.set_default_header("Authorization", f'Bearer {os.getenv("token")}')
        # self.api_client.set_default_header("content_type", 'application/pdf')
        # self.api_client.set_default_header("file_name", 'summary.pdf')
        self.api_instance = openapi_client.DefaultApi(self.api_client)

    @classmethod
    def teardown_class(self):
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test end."
        )
        # cls.api_client.close()

    # aws cognito-idp initiate-auth --region ap-northeast-1 --auth-flow USER_PASSWORD_AUTH --client-id 78dihnoo69jeen0d0e76j6ai0e  --auth-parameters USERNAME=cuihubin@amazon.com,PASSWORD=TEST123!
    upload_success_msg = 'The S3 presigned url is generated'
    upload_prefix_data = 'https://intelli-agent-apiconstructllmbotdocument'
    def test_01_upload_document_pdf(self):
        logger.info(f"test_01_upload_document_pdf start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='application/pdf', file_name="summary.pdf")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_01_upload_document_pdf end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_01_upload_document_pdf test failed"
    
    def test_02_upload_document_doc(self):
        logger.info(f"test_02_upload_document_doc start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', file_name="summary.doc")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_02_upload_document_doc end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_02_upload_document_doc test failed"
    
    def test_03_upload_document_csv(self):
        logger.info(f"test_03_upload_document_csv start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='text/csv', file_name="summary.csv")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_03_upload_document_csv end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_03_upload_document_csv test failed"

    def test_04_upload_document_html(self):
        logger.info(f"test_04_upload_document_html start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='text/html', file_name="summary.html")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_04_upload_document_html end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_04_upload_document_html test failed"
    
    def test_05_upload_document_jpeg(self):
        logger.info(f"test_05_upload_document_jpeg start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='image/jpeg', file_name="summary.jpeg")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_05_upload_document_jpeg end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_05_upload_document_jpeg test failed"
    
    def test_06_upload_document_jpg(self):
        logger.info(f"test_06_upload_document_jpg start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='image/jpeg', file_name="summary.jpg")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_06_upload_document_jpg end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_06_upload_document_jpg test failed"
    
    def test_07_upload_document_png(self):
        logger.info(f"test_07_upload_document_png start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='image/png', file_name="summary.png")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_07_upload_document_png end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_07_upload_document_png test failed"
    
    def test_08_upload_document_json(self):
        logger.info(f"test_08_upload_document_json start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='application/json', file_name="summary.json")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_08_upload_document_json end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_08_upload_document_json test failed"
    
    def test_09_upload_document_md(self):
        logger.info(f"test_09_upload_document_md start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='text/markdown', file_name="summary.md")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_09_upload_document_md end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_09_upload_document_md test failed"
    
    def test_10_upload_document_txt(self):
        logger.info(f"test_10_upload_document_txt start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='text/plain', file_name="summary.txt")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_10_upload_document_txt end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_10_upload_document_txt test failed"

    def test_11_upload_document_jsonl(self):
        logger.info(f"test_11_upload_document_jsonl start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='application/jsonlines', file_name="summary.jsonl")
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        logger.info("test_11_upload_document_jsonl end.")
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_11_upload_document_jsonl test failed"

        # response = json.loads(api_response.response.data.decode('utf-8'))
        # assert 1==1
        # with ApiClient(self.configuration) as api_client:
        # # Create an instance of the API class
        #     api_instance = DefaultApi(api_client)

        #     try:
        #         api_instance.etl_upload_s3_url_post()
        #     except Exception as e:
        #         print("Exception when calling DefaultApi->etl_upload_s3_url_post: %s\n" % e)
        # logger.info("test_1_add_account start ...")
        # source_new_account = SourceNewAccount(
        #     account_id=config.admin_account_id,
        #     account_provider=config.admin_account_provider_id,
        #     region=config.admin_account_region
        # )
        # logger.info("test_1_add_account test start >>>>>>>>>>>>>>>>>")
        # api_response = self.api_instance.add_account_data_source_add_account_post(
        #     source_new_account
        # )
        # logger.info("test_1_add_account test completed,result is >>>>>>>>>>>>>>>>>")
        # logger.info(json.loads(api_response.response.data.decode('utf-8'))["code"])
        # logger.info("test_1_add_account end .")
        # check_point(f"Check the account {config.admin_account_id} is added")
        # assert json.loads(api_response.response.data.decode('utf-8'))["code"] == 1001, "Add aws account failed"

