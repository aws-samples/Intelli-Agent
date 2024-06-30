import datetime
from decimal import Decimal
import json
import os
import traceback
from dotenv import load_dotenv
from api_test.test_case.utils import step
import config
# from sdps_api_test.utils.const import SDPSConst
import logging
import boto3
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# from business_logic.sdps import openapi_client
# # from business_logic.sdps import openapi_client
# from business_logic.sdps.openapi_client.apis.tags import data_source_api
# from business_logic.sdps.openapi_client.model.source_new_account import SourceNewAccount
# from business_logic.sdps.openapi_client.model.query_condition import QueryCondition
# from business_logic.sdps.openapi_client.model.new_data_source import NewDataSource
# from business_logic.sdps.openapi_client.model.account_info import AccountInfo
# from business_logic.sdps.openapi_client.model.jdbc_instance_source import JDBCInstanceSource
# from business_logic.sdps.openapi_client.model.admin_account_info import AdminAccountInfo
# from business_logic.sdps.openapi_client.model.jdbc_instance_source_base import JDBCInstanceSourceBase
# from solution_api_test_framework.service_helper.rds_helper import RDSHelper
# from solution_api_test_framework.service_helper.s3_helper import S3Helper
# from solution_api_test_framework.data_provider.data_provider import DataProvider


logger = logging.getLogger(__name__)
sts = boto3.client('sts')
caller_identity = boto3.client('sts').get_caller_identity()
partition = caller_identity['Arn'].split(':')[1]

class TestDocument:
    """DataSourceDiscovery test stubs"""

    @classmethod
    def setup_class(self):
        load_dotenv()
        logger.info(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}]API Test start..."
        )
        self.configuration = openapi_client.Configuration(
            host = os.getenv("api_url")
        )
        self.configuration.api_key['token'] = os.environ["token"]
        print(f"!!!!!configuration is {self.configuration}")


    @classmethod
    def teardown_class(self):
        logger.info("Teardown class")
        # cls.api_client.close()

    def test_1_upload_document_pdf(self):
        with openapi_client.ApiClient(self.configuration) as api_client:
        # Create an instance of the API class
            api_instance = openapi_client.DefaultApi(api_client)

            try:
                api_instance.etl_upload_s3_url_post()
            except Exception as e:
                print("Exception when calling DefaultApi->etl_upload_s3_url_post: %s\n" % e)
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

