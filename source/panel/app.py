from dotenv import load_dotenv
import os
from PyPDF2 import PdfReader
import streamlit as st
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.callbacks import get_openai_callback
import boto3
import requests
import json
import time

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Create an S3 client
s3 = boto3.client('s3')
glue = boto3.client('glue')
# load the job name from environment variable and convert it to string like 'PythonShellJobB6964098-YYlLj16uCsAn'
glue_job_name = str(os.getenv('GLUE_JOB_NAME'))

def process_text(text):
    # Split the text into chunks using langchain
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)

    # Convert the chunks of text into embeddings to form a knowledge base, should aware of the Rate limit.
    # Prompt like "reached for text-embedding-ada-002 in organization org-xx on tokens per min. Limit: 150000 / min. Current: 1 / min.≈
    embeddings = OpenAIEmbeddings()
    knowledgeBase = FAISS.from_texts(chunks, embeddings)
    
    return knowledgeBase

def get_job_runs(page_token=None):
    if page_token:
        response = glue.get_job_runs(JobName=glue_job_name, MaxResults=10, NextToken=page_token)
    else:
        response = glue.get_job_runs(JobName=glue_job_name, MaxResults=10)
    # function only return running aws glue jobs
    job_runs = [job_run for job_run in response['JobRuns'] if job_run['JobRunState'] == 'RUNNING']
    return job_runs, response.get('NextToken'), response.get('PreviousToken')

def pipeline_tab():
    st.title("LLM Bot ETL Pipeline")
    # text box to allow user input the url address of the pipeline with default value
    pipeline_url = st.text_input('Pipeline URL', value=os.getenv('PIPELINE_URL'))

    col1, col2 = st.columns(2)
    with col1:
        # sub panel to upload pdf and trigger the pipeline
        st.subheader('Online ETL Job')
        # adjust the width of the file uploader and hint text
        pdf = st.file_uploader('Upload your Document', type='pdf')

        if pdf is not None:
            # upload the pdf onto s3 bucket created in CDK stack with fixed prefix 'documents' , and trigger the pipeline
            s3.upload_fileobj(pdf, os.getenv('S3_BUCKET'), 'documents/' + pdf.name)

        # add hint text to tell user that the online ETL job will be triggered automatically after the pdf is uploaded
        st.markdown('**Note:** The online ETL job will be triggered automatically after the pdf is uploaded.')

    with col2:
        # sub panel to operate and monitor the offline ETL job running on AWS Glue
        # input box to allow user input request body and specify endpoint url and button to trigger the request sending to the endpoint
        st.subheader('Offline ETL Job')

        # dropdown to list all available s3 bucket and allow user to select one for further operation
        s3_buckets = s3.list_buckets()
        s3_bucket_names = [bucket['Name'] for bucket in s3_buckets['Buckets']]
        s3_bucket_name = st.selectbox('Select S3 Bucket', s3_bucket_names)

        # dropdown to list all subfolders under the selected s3 bucket and allow user to select one for further operation
        s3_objects = s3.list_objects(Bucket=s3_bucket_name)
        s3_object_names = [obj['Key'] for obj in s3_objects['Contents']]
        s3_object_name = st.selectbox('Select S3 Object', s3_object_names)

        # simple checkboxed to allow user select options to trigger the pipeline
        col3, col4 = st.columns(2)
        with col3:
            documentEnhance = st.checkbox('Doc Enhance')
            qaPairEnhance = st.checkbox('QA Pair Enhance')
        with col4:
            keyWordExtract = st.checkbox('Key Word Extract')
            textSummarize = st.checkbox('Text Summarize')

        # request body to be sent to the endpoint
        request_body = {
            's3Bucket': s3_bucket_name,
            's3Prefix': s3_object_name,
            'documentEnhance': documentEnhance,
            'qaEnhance': str(qaPairEnhance),
            'keyWordExtract': keyWordExtract,
            'textSummarize': textSummarize,
            'offline': True
        }
        # send button to trigger the request sending to the endpoint with s3_bucket_name and s3_object_name as request body, in conform with
        send_button = st.button('Start Offline Job')
        if send_button:
            response = requests.post(pipeline_url + '/etl', json=request_body, headers={'Content-Type': 'application/json'})
            st.text_area('Response:', value=response.text, height=200, max_chars=None)

    # progress bar to show the offline ETL job running status
    st.subheader('AWS Glue Job Status')

    # Initialize session state for pagination
    if 'next_token' not in st.session_state:
        st.session_state['next_token'] = None

    # Layout for buttons
    left_col, right_col = st.columns(2)
    with left_col:
        refresh_button = st.button('Refresh')

    with right_col:
        placeholder, prev_button, next_button = st.columns([3, 1, 1])
        with prev_button:
            if st.button('Prev'):
                st.session_state['next_token'] = st.session_state.get('new_prev_token')
        with next_button:
            if st.button('Next'):
                st.session_state['next_token'] = st.session_state.get('new_next_token')

    if refresh_button or 'next_token' in st.session_state:
        response, st.session_state['new_next_token'], st.session_state['new_prev_token'] = get_job_runs(st.session_state['next_token'])
        # Display the running glue jobs
        job_runs_container = ""
        total_job_runs = len(response)
        for job_run in response:
            job_runs_container += (f"Job Run ID: {job_run['Id']}")
            job_runs_container += (f" Retries: {job_run.get('Attempt', 'N/A')}")
            job_runs_container += (f" Start Time: {job_run['StartedOn']}")
            job_runs_container += (f" Duration: {job_run.get('ExecutionTime', 'N/A')} seconds\n")
        st.text_area('Running AWS Glue Jobs in total: ' + str(total_job_runs), value=job_runs_container, height=200, max_chars=None)

    # sub pannel to query and search the embedding in AOS
    st.subheader('Query and Search AOS')
    query = st.text_input('Input your query body here', value='{"aos_index": "chatbot-index", "query": {"operation": "match_all", "match_all": {}}}')
    # send button to trigger the request sending to the endpoint with query as request body
    request_body = {
        'aos_index': 'chatbot-index',
        'operation': 'match_all',
        'body': ''
    }
    send_button = st.button('Send')
    if send_button:
        response = requests.get(pipeline_url + '/embedding', json=request_body, headers={'Content-Type': 'application/json'})
        st.text_area('Response:', value=response.text, height=200, max_chars=None)

def llm_bot_tab():
    # user input box to allow user input question
    st.title("LLM Bot")
    query = st.text_input('Ask a question to the PDF')
    # cancel button to allow user to cancel the question
    cancel_button = st.button('Cancel')
    if cancel_button:
        st.stop()
    # send button to trigger the request sending to the endpoint with query as request body
    send_button = st.button('Send')
    if send_button:
        # request body to be sent to the endpoint
        request_body = {
            "model": "knowledge_qa",
            "messages": [
                {
                "role": "user",
                "content": query
                }
            ],
            "temperature": 0.7
        }
        response = requests.post(os.getenv('PIPELINE_URL') + '/llm', json=request_body, headers={'Content-Type': 'application/json'})
        try:
            data_dict = json.loads(response.text)
            content = data_dict["choices"][0]["message"]["content"]
            st.text_area('Response:', value=content.encode('utf-8').decode('utf-8'), height=200, max_chars=None)
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse response as JSON: {e}")
            st.text(response.text)
        # data_dict = response.text.json()
        # content = data_dict["choices"][0]["message"]["content"]
        # st.text_area('Response:', value=content.encode('utf-8').decode('unicode_escape'), height=200, max_chars=None)

def main():
    # Create a tab bar
    st.sidebar.title("LLM Bot")
    tabs = ["ETL Pipeline", "LLM Bot"]
    page = st.sidebar.radio("Select a tab", tabs)
    if page == "ETL Pipeline":
        pipeline_tab()
    elif page == "LLM Bot":
        llm_bot_tab()

    # using libary and OpenAI for local testing, comment for now
    
    # if pdf is not None:
    #     pdf_reader = PdfReader(pdf)
    #     # Text variable will store the pdf text
    #     text = ""
    #     for page in pdf_reader.pages:
    #         text += page.extract_text()
        
    #     # Create the knowledge base object
    #     knowledgeBase = process_text(text)
        
    #     query = st.text_input('Ask a question to the PDF')
    #     cancel_button = st.button('Cancel')
        
    #     if cancel_button:
    #         st.stop()
        
    #     if query:
    #         docs = knowledgeBase.similarity_search(query)
    #         llm = OpenAI()
    #         chain = load_qa_chain(llm, chain_type='stuff')
            
    #         with get_openai_callback() as cost:
    #             response = chain.run(input_documents=docs, question=query)
    #             print(cost)
                
    #         st.write(response)

if __name__ == "__main__":
    main()