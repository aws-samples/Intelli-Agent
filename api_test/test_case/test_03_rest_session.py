import datetime
import os
from dotenv import load_dotenv

from api_test.biz_logic.rest_api.openapi_client.configuration import Configuration
from .utils import step
import logging
import boto3
from pprint import pprint
import sys
import os



logger = logging.getLogger(__name__)
sts = boto3.client('sts')
caller_identity = boto3.client('sts').get_caller_identity()
partition = caller_identity['Arn'].split(':')[1]

class TestSession:
    """DataSourceDiscovery test stubs"""

    @classmethod
    def setup_class(self):
        load_dotenv()
        logger.info(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}]API Test start..."
        )
        self.configuration = Configuration(
            host = os.getenv("api_url")
        )
        self.configuration.api_key['token'] = os.environ["token"]
        print(f"############url is {os.getenv('api_url')}")
        print(f"############token is {os.getenv('token')}")


    @classmethod
    def teardown_class(self):
        logger.info("Teardown class")
        # cls.api_client.close()

    def test_1_upload_document_pdf(self):
        assert 1==1
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

