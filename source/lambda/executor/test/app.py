import gradio as gr
import json
import requests
import boto3
from websocket import create_connection
from executor_local_test import generate_answer
from langchain_community.document_loaders import UnstructuredPDFLoader


doc_dict = {}
s3 = boto3.client('s3')
max_debug_block = 20

import os

def load_raw_data():
    global doc_dict
    raw_data = json.load(
        open("/home/ubuntu/Project/llm-bot/src/lambda/test/dgr_csdc_0830_1013_doc.json")
    )
    for data in raw_data:
        doc_dict[data["source"]] = json.dumps(data)
    raw_data = json.load(
        open("/home/ubuntu/Project/llm-bot/src/lambda/test/ug_add_api_tag.json")
    )
    # raw_data = json.load(open("/home/ubuntu/Project/llm-bot/src/lambda/test/webcrawl_industry_aws_20231205_ug_en.json"))
    for data in raw_data:
        doc_dict[data["url"]] = json.dumps(data)


def check_data(url):
    if url in doc_dict:
        return doc_dict[url]
    return {"error": "url not found"}


text = [
    # [
    #     "在相同的EMR Serverless应用程序中，不同的Job可以共享Worker吗？",
    # ],
    # [
    #     "如何授予用户对Athena只读权限?",
    # ],
    # [
    #     "是否可以在Site to Site VPN连接上设置BGP秘钥？",
    # ],
    # [
    #     "可以在AWS Application Loadbalancer中启用预热功能么？",
    # ],
    [
        "What is MaxiCharger AC Elite (residential)",
    ],
    [
        "How to install the holster",
    ],
    [
        "What is the intended use of Autel MaxiCharger AC Wallbox",
    ],
    [
        "义乌华鼎锦纶股份有限公司远期结售汇交易金额上限",
    ],
    [
        "天工国际更正原因",
    ],
    [
        "建发股份向关联人销 售商品、提供 劳务2024年预计总金额交是多少",
    ],
    [
        "建发股份和四川永丰浆纸股份有限公司及其子公司向关联人销 售商品、提供劳务交易预计总金额总计多少",
    ],
    [
        "员工连续旷工两天会被处以什么处分？"
    ],
]

def generate_answer_from_api(url, query_input, type, rag_parameters):
    data = {
        "model": "knowledge_qa",
        "messages": [{"role": "user", "content": query_input}],
        "type": type,
    }
    data.update(rag_parameters)
    response = requests.post(url, json.dumps(data))
    return response

def generate_answer_from_ws(api_type, url, query_input, type):
    gr_tab_list = []
    gr_json_list = []
    for i in range(max_debug_block):
        with gr.Tab(visible=False) as gr_tab:
            gr_tab_list.append(gr_tab)
            gr_json_block = gr.JSON(visible=False)
            gr_json_list.append(gr_json_block)
    model_id = "internlm2-chat-7b"
    # endpoint_name = "instruct-internlm2-chat-7b-f7dc2"
    # endpoint_name = "internlm2-chat-7b-2024-02-23-07-29-02-632"
    endpoint_name = "internlm2-chat-20b-4bits-2024-02-29-05-37-42-885"
    rag_parameters=dict()
    # rag_parameters=dict(
    #     query_process_config = {
    #         "conversation_query_rewrite_config":{
    #             "model_id":model_id,
    #             "endpoint_name":endpoint_name
    #         },
    #         "translate_config":{
    #             "model_id":model_id,
    #             "endpoint_name": endpoint_name
    #         }
    #     },
    #     retriever_config = {
    #         "chunk_num": 0,
    #         "using_whole_doc": False,
    #         "enable_reranker": True,
    #         "retriever_top_k": 2,
    #         "workspace_ids": ["aos_index_mkt_faq_qq", "aos_index_acts_qd"]
    #     },
    #     generator_llm_config ={
    #         "model_kwargs":{
    #             "max_new_tokens": 2000,
    #             "temperature": 0.1,
    #             "top_p": 0.9
    #         },
    #         "model_id": model_id,
    #         "endpoint_name": endpoint_name,
    #         "context_num": 2
    #     })
    sources = []
    debug_info = []
    ws = create_connection(url, timeout=100)
    data = {
        "model": "knowledge_qa",
        "messages": [{"role": "user", "content": query_input}],
        "type": type,
        "get_contexts": False,
        "enable_debug": False,
    }
    data.update(rag_parameters)
    ws.send(json.dumps(data))
    answer = ""
    while True:
        ret = json.loads(ws.recv())
        try:
            message_type = ret['choices'][0]['message_type']
        except:
            print(ret)
            raise
        if message_type == "START":
            continue 
        elif message_type == "CHUNK":
            print(ret['choices'][0]['message']['content'],end="",flush=True)
            answer += ret['choices'][0]['message']['content']
            yield answer, "", *gr_tab_list, *gr_json_list
        elif message_type == "END":
            break
        elif message_type == "ERROR":
            print(ret['choices'][0]['message']['content'])
            break 
        elif message_type == "CONTEXT":
            print()
            print('contexts',ret)
            sources = ret['choices'][0]["knowledge_sources"]
            # debug_info = ret['choices'][0]["debug_info"]
            debug_info = {}
            yield answer, sources, *render_debug_info(debug_info)
        else:
            break
    ws.close()

def generate_answer_from_local(api_type, url_input, query_input, entry_type):
    model_id = "internlm2-chat-7b"
    endpoint_name = "instruct-internlm2-chat-7b-f7dc2"
    # endpoint_name = "internlm2-chat-7b-2024-02-23-07-29-02-632"
    # endpoint_name = "internlm2-chat-7b-4bits-2024-02-28-07-08-57-839"
    rag_parameters=dict(
    #     query_process_config = {
    #         "conversation_query_rewrite_config":{
    #             "model_id":model_id,
    #             "endpoint_name":endpoint_name
    #         },
    #         "translate_config":{
    #             "model_id":model_id,
    #             "endpoint_name": endpoint_name
    #         }
    #     },
        retriever_config = {
            "qq_config": {
                "qq_match_threshold": 0.8,
                "retriever_top_k": 5,
                "query_key": "query"
            },
            "qd_config":{
                "retriever_top_k": 10,
                "context_num": 2,
                "using_whole_doc": False,
                "reranker_top_k": 10,
                # "reranker_type": RerankerType.BYPASS.value,
                "reranker_type": "bge_reranker",
                # "reranker_type": RerankerType.BGE_M3_RERANKER.value,
                "qd_match_threshold": 2,
                "query_key":"conversation_query_rewrite"
                # "enable_reranker":True
            },
            # "workspace_ids": ["aos_index_mkt_faq_qq_m3", "aos_index_acts_qd_m3", "aos_index_mkt_faq_qd_m3", "aos_index_repost_qq_m3"]
        },
    #     generator_llm_config ={
    #         "model_kwargs":{
    #             "max_new_tokens": 2000,
    #             "temperature": 0.1,
    #             "top_p": 0.9
    #         },
    #         "model_id": model_id,
    #         "endpoint_name": endpoint_name,
    #         "context_num": 1
    #     }
    )
    rag_parameters = {
        "retriever_config": {
            "qq_config" : {
                "enable_debug": True
            },
            "qd_config" : {
                "enable_debug": True
            }
        }
    }
    sources = []
    debug_info = []
    answer, sources, debug_info = generate_answer(
        query=query_input, type=entry_type, rag_parameters=rag_parameters, enable_debug=True)
    return answer, sources, *render_debug_info(debug_info) 

def test(api_type, url_input, query_input, entry_type):
    return "yyyy", "yy"

def generate_func(api_type, url_input, query_input, entry_type):
    if api_type == "local":
        return generate_answer_from_local(api_type, url_input, query_input, entry_type)
    elif api_type == "cloud":
        return generate_answer_from_ws(api_type, url_input, query_input, entry_type)

def render_debug_info(debug_info):
    tab_list = []
    json_list = []
    json_count = 0
    accordion_count = 0
    for i, info_key in enumerate(debug_info.keys()):
        tab_list.append(gr.Tab(label=info_key, visible=True))
        accordion_count += 1
        if type(debug_info[info_key]) == str:
            json_value = {info_key: debug_info[info_key]}
        else:
            json_value = debug_info[info_key]
        json_list.append(gr.JSON(value=json_value, visible=True))
        json_count += 1
    for i in range(max_debug_block-accordion_count):
        tab_list.append(gr.Tab(visible=False))
    for i in range(max_debug_block-json_count):
        json_list.append(gr.JSON(value=["dummy"], visible=False))
    return *tab_list, *json_list

def invoke_etl_online(
    url_input, s3_bucket_chunk_input, s3_prefix_chunk_input, need_split_dropdown
):
    request_body = {
        "s3_bucket": s3_bucket_chunk_input,
        "s3_prefix": s3_prefix_chunk_input,
        "need_split": need_split_dropdown,
    }

    response = requests.post(
        url_input + "/extract",
        json=request_body,
        headers={"Content-Type": "application/json"},
    )
    response_json = response.json()
    print("Response JSON:", response_json)

    return response_json


def get_etl_status(url_input, sfn_input):
    if ":" in sfn_input:
        execution_id = sfn_input.split(":")[-1]
    else:
        execution_id = sfn_input
    print(execution_id)
    params = {"executionId": execution_id}
    response = requests.get(
        url_input + "/etl/status",
        headers={"Content-Type": "application/json"},
        params=params,
    )

    response_json = response.json()
    print("Response JSON:", response_json)

    return response_json


def invoke_etl_offline(
    url_input,
    s3_bucket_input,
    s3_prefix_input,
    offline_dropdown,
    qa_dropdown,
    aos_index_input,
):
    request_body = {
        "s3Bucket": s3_bucket_input,
        "s3Prefix": s3_prefix_input,
        "offline": offline_dropdown,
        "qaEnhance": qa_dropdown,
        "aosIndex": aos_index_input,
    }

    response = requests.post(
        url_input + "/etl",
        json=request_body,
        headers={"Content-Type": "application/json"},
    )
    response_json = response.json()
    print("Response JSON:", response_json)

    return response_json, response_json["step_function_arn"]


def load_s3_bucket():
    s3_buckets = s3.list_buckets()
    s3_bucket_names = [bucket['Name'] for bucket in s3_buckets['Buckets']]

    return s3_bucket_names


def load_s3_doc(s3_bucket_dropdown, s3_prefix_compare):
    if not s3_bucket_dropdown:
        return []
    response = s3.get_object(Bucket=s3_bucket_dropdown, Key=s3_prefix_compare)
    content = response['Body'].read().decode('utf-8')
    
    return content

def get_all_keys(bucket_name, prefix):
    if not bucket_name:
        return []
    key_list = []
    # Create a reusable Paginator
    paginator = s3.get_paginator('list_objects_v2')

    # Create a PageIterator from the Paginator
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    for page in page_iterator:
        if "Contents" in page:
            # Print the keys (file names)
            for key in page['Contents']:
                key_list.append(key['Key'])
    return key_list


def load_by_langchain(s3_bucket_dropdown, s3_prefix_compare):
    file_name = s3_prefix_compare.split("/")[-1]
    local_file_path = f"./{file_name}"
    resp = s3.download_file(s3_bucket_dropdown, s3_prefix_compare, local_file_path)
    loader = UnstructuredPDFLoader(local_file_path)
    data = loader.load()

    return data


with gr.Blocks() as demo:
    s3_bucket_name_list = load_s3_bucket()
    gr.Markdown("LLM Bot Debug UI")
    gr_url_input = gr.Text(
        label="Url, eg. https://f2zgexpo47.execute-api.us-east-1.amazonaws.com/v1/"
    )
    gr_websocket_input = gr.Text(
        label="Websocket, eg. wss://2ogbgobue2.execute-api.us-west-2.amazonaws.com/prod/",
        value='wss://2ogbgobue2.execute-api.us-west-2.amazonaws.com/prod/'
    )
    with gr.Tab("Chat"):
        gr_api_type = gr.Dropdown(label="API", choices=["local", "cloud"], value="local")
        gr_entry_input = gr.Dropdown(label="Entry", choices=["common", "market_chain", "dgr"], value="market_chain")
        gr_query_input = gr.Text(label="Query")
        gr_local_answer_btn = gr.Button(value="Local Answer")
        gr_cloud_answer_btn = gr.Button(value="Cloud Answer")
        gr_answer_output = gr.Text(label="Anwser", show_label=True)
        gr_sources_output = gr.Text(label="Sources", show_label=True)
        gr_tab_list = []
        gr_json_list = []
        for i in range(max_debug_block):
            with gr.Tab(visible=False) as gr_tab:
                gr_tab_list.append(gr_tab)
                gr_json_block = gr.JSON(visible=False)
                gr_json_list.append(gr_json_block)

        # with gr.Accordion("QueryParserDebugInfo", open=False):
        #     query_parser_debuge_info = gr.JSON()
        # with gr.Accordion("QQMatcherDebugInfo", open=False):
        #     qq_match_debuge_info = gr.JSON()
        # with gr.Accordion("KNNRetrieverDebugInfo", open=False):
        #     knn_retriever_debug_info = gr.JSON()
        #     with gr.Accordion("index-1", open=False):
        #         knn_retriever_debug_info = gr.JSON()
        # with gr.Accordion("BooleanRetrieverDebugInfo", open=False):
        #     boolean_retriever_debug_info = gr.JSON()
        # with gr.Accordion("CombineRetrieverDebugInfo", open=False):
        #     combine_retriever_debug_info = gr.JSON()
        # with gr.Accordion("CrossModelDebugInfo", open=False):
        #     cross_model_debug_info = gr.JSON()
        # with gr.Accordion("LLMDebugInfo", open=False):
        #     llm_debug_info = gr.JSON()
        context = None
        gr_local_answer_btn.click(
            generate_answer_from_local,
            inputs=[gr_api_type, gr_websocket_input, gr_query_input, gr_entry_input],
            outputs=[
                gr_answer_output,
                gr_sources_output,
                *gr_tab_list,
                *gr_json_list
            ]
        )
        context = None
        gr_cloud_answer_btn.click(
            generate_answer_from_ws,
            inputs=[gr_api_type, gr_websocket_input, gr_query_input, gr_entry_input],
            outputs=[
                gr_answer_output,
                gr_sources_output,
                *gr_tab_list,
                *gr_json_list
            ]
        )


        # with gr.Accordion("RawDataDebugInfo", open=False):
        #     raw_data = gr.JSON()
        # check_btn = gr.Button(value="Check")
        # check_btn.click(check_data, inputs=[url_input], outputs=[raw_data])
        # gr.Examples(
        #     examples=text,
        #     inputs=[websocket_input, query_input, entry_input],
        #     fn=generate_func,
        #     cache_examples=False,
        # )

        # test_output = gr.Text(label="test_1", show_label=True)
        # test_output_2 = gr.Text(label="test_2", show_label=True)
        # test_btn = gr.Button(value="test")
        # test_btn.click(
        #     test,
        #     inputs=[gr_api_type, gr_websocket_input, gr_query_input, gr_entry_input],
        #     outputs=[
        #         test_output,
        #         test_output_2
        #     ]
        # )
    with gr.Tab("Data Process Offline"):
        with gr.Row():
            with gr.Column():
                s3_bucket_input = gr.Dropdown(
                    choices=s3_bucket_name_list,
                    label="S3 Bucket",
                    info="S3 bucket name, eg. llm-bot",
                )
            with gr.Column():
                s3_prefix_input = gr.Textbox(
                    label="S3 prefix, eg. demo_folder/demo.pdf"
                )
            with gr.Column():
                aos_index_input = gr.Textbox(label="OpenSearch index name, eg. dev")
        with gr.Row():
            with gr.Column():
                offline_dropdown = gr.Dropdown(
                    choices=["true", "false"],
                    label="Offline",
                    info="Wether to process the data offline, default is true",
                )
            with gr.Column():
                qa_dropdown = gr.Dropdown(
                    choices=["true", "false"],
                    label="QA Enhancement",
                    info="Wether to enable QA enhancement, after it is enabled, QA pairs will be generated by LLM according to the file content, default is false",
                )
        process_offline_button = gr.Button("Process Offline")
        with gr.Accordion("ETL Response", open=True):
            sfn_json = gr.JSON()
        sfn_input = gr.Textbox(label="Step function ARN or execution ID")
        process_offline_button.click(
            fn=invoke_etl_offline,
            inputs=[
                gr_url_input,
                s3_bucket_input,
                s3_prefix_input,
                offline_dropdown,
                qa_dropdown,
                aos_index_input,
            ],
            outputs=[sfn_json, sfn_input],
        )

        etl_status_button = gr.Button("Get Status")
        with gr.Accordion("ETL Get Status Response", open=True):
            status_output_json = gr.JSON()
        etl_status_button.click(
            fn=get_etl_status,
            inputs=[
                gr_url_input,
                sfn_input,
            ],
            outputs=[status_output_json],
        )
    with gr.Tab("Chunk Comparison"):
        with gr.Row():
            with gr.Column():
                s3_bucket_chunk_input = gr.Dropdown(
                    choices=s3_bucket_name_list,
                    label="S3 Bucket",
                    info="S3 bucket name, eg. llm-bot",
                )
            with gr.Column():
                s3_prefix_chunk_input = gr.Textbox(
                    label="S3 prefix, eg. demo_folder/demo.pdf"
                )
            with gr.Column():
                need_split_dropdown = gr.Dropdown(
                    choices=["true", "false"],
                    label="Need split",
                    info="Wether to split the content as chunks, default is false",
                )
        process_online_button = gr.Button("Process Online")
        with gr.Accordion("Online Result", open=True):
            online_result = gr.JSON()
        process_online_button.click(
            fn=invoke_etl_online,
            inputs=[
                gr_url_input,
                s3_bucket_chunk_input,
                s3_prefix_chunk_input,
                need_split_dropdown,
            ],
            outputs=[online_result],
        )
        with gr.Row():
            with gr.Column():
                lc_button = gr.Button("Compare with Unstructured")
            with gr.Column():
                pp_button = gr.Button("Compare with PPStructure")
        unstructured_md = gr.TextArea(label="Unstructured Output")
        lc_button.click(
            fn=load_by_langchain,
            inputs=[
                s3_bucket_chunk_input,
                s3_prefix_chunk_input,
            ],
            outputs=[unstructured_md],
        )

        with gr.Row():
            with gr.Column():
                s3_bucket_dropdown = gr.Dropdown(
                    choices=s3_bucket_name_list,
                    label="S3 Bucket",
                    info="S3 bucket name, eg. llm-bot",
                )
                s3_prefix_text = gr.Textbox(
                    label="S3 prefix, eg. demo_folder/demo.pdf"
                )
                get_split_file_button = gr.Button(value="List Files")
            with gr.Column():
                s3_prefix_dropdown = gr.Dropdown(
                    choices=[],
                    label="S3 prefix, eg. demo_folder/demo.pdf"
                )
                def update_s3_prefix_dropdown(s3_bucket, s3_prefix):
                    return gr.Dropdown(choices=get_all_keys(s3_bucket, s3_prefix))
                get_split_file_button.click(
                    fn=update_s3_prefix_dropdown,
                    inputs=[s3_bucket_dropdown, s3_prefix_text],
                    outputs=[s3_prefix_dropdown])
                load_button = gr.Button("Load")
        solution_md = gr.Text(label="Output")
        load_button.click(
            fn=load_s3_doc,
            inputs=[
                s3_bucket_dropdown,
                s3_prefix_dropdown,
            ],
            outputs=[solution_md],
        )

# load_raw_data()
if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="0.0.0.0", share=True, server_port=8080)