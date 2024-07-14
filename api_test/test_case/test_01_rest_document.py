import datetime
import os
import time
# import api_test.config as config
from dotenv import load_dotenv
import pytest
import requests

from api_test.biz_logic.rest_api import openapi_client
# from api_test.biz_logic.rest_api import IntellapiconnnHdtwRWUXa

from .utils import step
import logging
import boto3

logger = logging.getLogger(__name__)
sts = boto3.client('sts')
s3_client = boto3.client('s3')
caller_identity = boto3.client('sts').get_caller_identity()
partition = caller_identity['Arn'].split(':')[1]

# aws cognito-idp admin-set-user-password \
#   --user-pool-id us-east-1_mnQ87vF26 \
#   --username cuihubin@amazon.com \
#   --password TEST123! \
#   --permanent

# aws cognito-idp initiate-auth \
#     --region us-east-1 \
#     --auth-flow USER_PASSWORD_AUTH \
#     --client-id p880fbijno32gtp2o0i651ukl \
#     --auth-parameters USERNAME=cuihubin@amazon.com,PASSWORD=CSDC23!

class TestDocument:
    """DataSourceDiscovery test stubs"""

    @classmethod
    def setup_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test start..."
        )
        load_dotenv()
        cls.configuration = openapi_client.Configuration(host=os.getenv('rest_api_url'))
        cls.api_client = openapi_client.ApiClient(cls.configuration)
        cls.api_client.set_default_header("Authorization", f'Bearer {os.getenv("token")}')
        cls.api_instance = openapi_client.DefaultApi(cls.api_client)
        cls.fileTypeDict = {
            "pdf":"application/pdf",
            "docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "csv":"text/csv",
            "html":"text/html",
            "jpeg":"image/jpeg",
            "jpg":"image/jpeg",
            "png":"image/png",
            "json":"application/json",
            "md":"text/markdown",
            "txt":"text/plain",
            "jsonl":"application/jsonlines"

        }
        cls.exeIdDict = {}
        # self.exeIdDict = {}

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
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='application/pdf', file_name="summary.pdf")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_01_upload_document_pdf test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.pdf")
        logger.info("test_01_upload_document_pdf end.")

    def test_02_upload_document_docx(self):
        '''test case'''
        logger.info("test_02_upload_document_docx start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', file_name="summary.doc")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_02_upload_document_docx test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.docx")
        logger.info("test_02_upload_document_docx end.")

    def test_03_upload_document_csv(self):
        '''test case'''
        logger.info("test_03_upload_document_csv start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='text/csv', file_name="summary.csv")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_03_upload_document_csv test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.csv")
        logger.info("test_03_upload_document_csv end.")

    def test_04_upload_document_html(self):
        '''test case'''
        logger.info("test_04_upload_document_html start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='text/html', file_name="summary.html")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_04_upload_document_html test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.html")
        logger.info("test_04_upload_document_html end.")

    def test_05_upload_document_jpeg(self):
        '''test case'''
        logger.info("test_05_upload_document_jpeg start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='image/jpeg', file_name="summary.jpeg")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_05_upload_document_jpeg test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.jpeg")
        logger.info("test_05_upload_document_jpeg end.")
    
    def test_06_upload_document_jpg(self):
        '''test case'''
        logger.info("test_06_upload_document_jpg start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='image/jpeg', file_name="summary.jpg")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_06_upload_document_jpg test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.jpg")
        logger.info("test_06_upload_document_jpg end.")
    
    def test_07_upload_document_png(self):
        '''test case'''
        logger.info("test_07_upload_document_png start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='image/png', file_name="summary.png")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_07_upload_document_png test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.png")
        logger.info("test_07_upload_document_png end.")
    
    def test_08_upload_document_json(self):
        '''test case'''
        logger.info("test_08_upload_document_json start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='application/json', file_name="summary.json")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_08_upload_document_json test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.json")
        logger.info("test_08_upload_document_json end.")
    
    def test_09_upload_document_md(self):
        '''test case'''
        logger.info("test_09_upload_document_md start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='text/markdown', file_name="summary.md")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_09_upload_document_md test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.md")
        logger.info("test_09_upload_document_md end.")
    
    def test_10_upload_document_txt(self):
        '''test case'''
        logger.info("test_10_upload_document_txt start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='text/plain', file_name="summary.txt")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_10_upload_document_txt test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.txt")
        logger.info("test_10_upload_document_txt end.")

    def test_11_upload_document_jsonl(self):
        '''test case'''
        logger.info("test_11_upload_document_jsonl start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='application/jsonlines', file_name="summary.jsonl")
        response = self.api_instance.etl_upload_s3_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_11_upload_document_jsonl test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.jsonl")
        logger.info("test_11_upload_document_jsonl end.")
    
    def test_12_list_document(self):
        '''test case'''
        logger.info("test_12_list_document start ....")
        response = self.api_instance.etl_list_execution_get(page_size='9999', max_items='9999')
        logger.info("test_12_list_document end.")
        for item in response.items:
            print(f"item is {item}")
            key = item.s3_prefix.rsplit('.', 1)[-1]
            print(f"key is {key}")
            self.exeIdDict[key]=item.execution_id
            # self.exeIdDict[key] = item.execution_id
        assert response.count>0, "test_12_list_document test failed"

    def test_13_exec_document_pdf(self):
        '''test case'''
        # print(f"self.exeIdDict is ===== {self.exeIdDict}")
        time.sleep(10 * 60)
        logger.info("test_13_exec_document_pdf start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["pdf"])
        print(f"test_13_exec_document_pdf end. res is {response}")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_13_exec_document_pdf test failed"
    
    def test_14_exec_document_docx(self):
        '''test case'''
        logger.info("test_14_exec_document_docx start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["docx"])
        logger.info("test_14_exec_document_docx end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_14_exec_document_docx test failed"

    def test_15_exec_document_csv(self):
        '''test case'''
        logger.info("test_15_exec_document_csv start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["csv"])
        logger.info("test_15_exec_document_csv end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_15_exec_document_csv test failed"

    def test_16_exec_document_html(self):
        '''test case'''
        logger.info("test_16_exec_document_html start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["html"])
        logger.info("test_16_exec_document_html end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_16_exec_document_html test failed"
    
    def test_17_exec_document_jpeg(self):
        '''test case'''
        logger.info("test_17_exec_document_jpeg start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["jpeg"])
        logger.info("test_17_exec_document_jpeg end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_17_exec_document_jpeg test failed"

    def test_18_exec_document_jpg(self):
        '''test case'''
        logger.info("test_18_exec_document_jpg start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["jpg"])
        logger.info("test_18_exec_document_jpg end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_18_exec_document_jpg test failed"

    def test_19_exec_document_png(self):
        '''test case'''
        logger.info("test_19_exec_document_png start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["png"])
        logger.info("test_19_exec_document_png end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_19_exec_document_png test failed"

    def test_20_exec_document_md(self):
        '''test case'''
        logger.info("test_20_exec_document_md start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["md"])
        logger.info("test_20_exec_document_md end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_20_exec_document_md test failed"

    def test_21_exec_document_txt(self):
        '''test case'''
        logger.info("test_21_exec_document_txt start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["txt"])
        logger.info("test_21_exec_document_txt end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_21_exec_document_txt test failed"

    def test_22_exec_document_jsonl(self):
        '''test case'''
        logger.info("test_22_exec_document_jsonl start ....")
        # param = openapi_client.IntellapicoDjp0ELR6YyaK()
        response = self.api_instance.etl_execution_get(execution_id=self.exeIdDict["jsonl"])
        logger.info("test_22_exec_document_jsonl end.")
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_22_exec_document_jsonl test failed"
    
    def test_23_delete_document(self):
        '''test case'''
        logger.info("test_23_delete_document start ....")
        param = openapi_client.IntellapicoLVFWYrm87vJk(executionId=list(self.exeIdDict.values()))
        response = self.api_instance.etl_delete_execution_post(param)
        logger.info("test_23_delete_document end.")
        assert response.message=="The deletion has completed", "test_23_delete_document test failed"

    def test_24_upload_mismatch_document(self):
        '''test case'''
        logger.info("test_24_upload_mismatch_document start ....")
        param = openapi_client.IntellapicoTvS3spqLZ3w9(content_type='application/jsonlines', file_name="summary.pdf")
        response = self.api_instance.etl_upload_s3_url_post(param)
        logger.info("test_24_upload_mismatch_document end.")
        assert response.message!=self.upload_success_msg, "test_24_upload_mismatch_document test failed"

    def __upload_file_to_s3(self, presigned_url, file_path):

        with open(file_path, 'rb') as file_data:
            headers = {
            'Content-Type': self.fileTypeDict[os.path.splitext(file_path)[1][1:]],  # or the appropriate content type
            }
            response = requests.put(presigned_url, data=file_data, headers=headers, timeout=600)
        if response.status_code == 200:
            logger.info("!!!!!!!!!!File uploaded successfully!!!!!!!!!!")
        else:
            logger.error("!!!!!!!!!!Failed to upload file!!!!!!!!!!")
            logger.info(response.content)
