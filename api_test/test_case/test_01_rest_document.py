'''TestDocument'''
import datetime
import os
import time
import logging
from dotenv import load_dotenv
import requests
import boto3
from api_test.biz_logic.rest_api import openapi_client
from .utils import step

logger = logging.getLogger(__name__)
sts = boto3.client('sts')
s3_client = boto3.client('s3')
caller_identity = boto3.client('sts').get_caller_identity()
partition = caller_identity['Arn'].split(':')[1]

class TestDocument:
    """DataSourceDiscovery test stubs"""
    upload_success_msg = 'The S3 presigned url is generated'
    upload_prefix_data = 'https://intelli-agent-apiconstructllmbotdocument'

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

    @classmethod
    def teardown_class(cls):
        '''test case'''
        step(
            f"[{datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')}] [{__name__}] Test end."
        )
    
    def setup_method(self, method):
        """Setup method to create a rest client connection before each test."""
        logger.info("%s start...", method.__name__)
    
    def teardown_method(self, method):
        """Setup method to create a rest client connection before each test."""
        logger.info("%s end.", method.__name__)
    
    def test_01_upload_document_pdf(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='application/pdf', file_name="summary.pdf")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_01_upload_document_pdf test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.pdf")

    def test_02_upload_document_docx(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', file_name="summary.docx")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_02_upload_document_docx test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.docx")

    def test_03_upload_document_csv(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='text/csv', file_name="summary.csv")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_03_upload_document_csv test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.csv")

    def test_04_upload_document_html(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='text/html', file_name="summary.html")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_04_upload_document_html test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.html")

    def test_05_upload_document_jpeg(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='image/jpeg', file_name="summary.jpeg")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_05_upload_document_jpeg test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.jpeg")
    
    def test_06_upload_document_jpg(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='image/jpeg', file_name="summary.jpg")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_06_upload_document_jpg test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.jpg")
    
    def test_07_upload_document_png(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='image/png', file_name="summary.png")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_07_upload_document_png test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.png")
    
    def test_08_upload_document_json(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='application/json', file_name="summary.json")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_08_upload_document_json test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.json")
    
    def test_09_upload_document_md(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='text/markdown', file_name="summary.md")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_09_upload_document_md test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.md")
    
    def test_10_upload_document_txt(self):
        '''test case'''
        param = openapi_client.IntellapicopALE5PXT4ttp(content_type='text/plain', file_name="summary.txt")
        response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
        assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_10_upload_document_txt test failed"
        self.__upload_file_to_s3(response.data, "./test_data/summary.txt")

    # def test_11_upload_document_jsonl(self):
    #     '''test case'''
    #     param = openapi_client.IntellapicopALE5PXT4ttp(content_type='application/jsonlines', file_name="summary.jsonl")
    #     response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
    #     assert response.message==self.upload_success_msg and response.data.startswith(self.upload_prefix_data), "test_11_upload_document_jsonl test failed"
    #     self.__upload_file_to_s3(response.data, "./test_data/summary.jsonl")
    
    def test_12_list_document(self):
        '''test case'''
        time.sleep(2 * 60)
        response = self.api_instance.knowledge_base_executions_get(page_size='9999', max_items='9999')
        logger.info("response>>>>>>>>>>>")
        logger.info(response) 
        for item in response.items:
            key = item.s3_prefix.rsplit('.', 1)[-1]
            self.exeIdDict[key]=item.execution_id 
        logger.info("file list>>>>>>>>>>>")
        logger.info(self.exeIdDict) 
        assert response.count>0, "test_12_list_document test failed"

    def test_13_exec_document_pdf(self):
        '''test case'''
        time.sleep(10 * 60)
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["pdf"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_13_exec_document_pdf test failed"
    
    def test_14_exec_document_docx(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["docx"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_14_exec_document_docx test failed"

    def test_15_exec_document_csv(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["csv"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_15_exec_document_csv test failed"

    def test_16_exec_document_html(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["html"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_16_exec_document_html test failed"
    
    def test_17_exec_document_jpeg(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["jpeg"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_17_exec_document_jpeg test failed"

    def test_18_exec_document_jpg(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["jpg"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_18_exec_document_jpg test failed"

    def test_19_exec_document_png(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["png"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_19_exec_document_png test failed"

    def test_20_exec_document_md(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["md"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_20_exec_document_md test failed"

    def test_21_exec_document_txt(self):
        '''test case'''
        response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["txt"])
        assert response.count==1 and response.items[0].status == "SUCCEED", "test_21_exec_document_txt test failed"

    # def test_22_exec_document_jsonl(self):
    #     '''test case'''
    #     response = self.api_instance.knowledge_base_executions_execution_id_get(execution_id=self.exeIdDict["jsonl"])
    #     assert response.count==1 and response.items[0].status == "SUCCEED", "test_22_exec_document_jsonl test failed"
    
    def test_23_delete_document(self):
        '''test case'''
        param = openapi_client.IntellapicobiGoe5Lboi9l(executionId=list(self.exeIdDict.values()))
        response = self.api_instance.knowledge_base_executions_delete(param)
        assert response.message=="The deletion has completed", "test_23_delete_document test failed"

    # def test_24_upload_mismatch_document(self):
    #     '''test case'''
    #     param = openapi_client.IntellapicopALE5PXT4ttp(content_type='application/jsonlines', file_name="summary.pdf")
    #     response = self.api_instance.knowledge_base_kb_presigned_url_post(param)
    #     assert response.message!=self.upload_success_msg, "test_24_upload_mismatch_document test failed"

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
