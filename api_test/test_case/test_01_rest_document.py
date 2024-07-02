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

    def test_01_upload_document_pdf(self):
        step(f"test_01_upload_document_pdf start ....")
        intellapico_kbf_xmyu1_w8_nr = openapi_client.IntellapicoKbfXMYu1W8Nr(content_type='application/pdf', file_name="summary.pdf")
        # intellapico_kbf_xmyu1_w8_nr.from_dict(payload)

        # # 创建请求 body 对象
        # request_body = ExampleRequestBody(
        #     attribute1='value1',
        #     attribute2='value2'
        # )

        # self.api_instance
        response = self.api_instance.etl_upload_s3_url_post(intellapico_kbf_xmyu1_w8_nr)
        # assert response.data
        # print(f'res is {response.data}')

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

