import gradio as gr
import json
from executor_local_test import generate_answer

doc_dict = {}

def load_raw_data():
    global doc_dict
    raw_data = json.load(open("/home/ubuntu/Project/llm-bot/src/lambda/test/dgr_csdc_0830_1013_doc.json"))
    for data in raw_data:
        doc_dict[data["source"]] = json.dumps(data)
    raw_data = json.load(open("/home/ubuntu/Project/llm-bot/src/lambda/test/ug_add_api_tag.json"))
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
        "建发股份和四川永丰浆纸股份有限公司及其子公司向关联人销 售商品、提供劳务交易预计总金额总计多少",
    ],
    [
        "建发股份向关联人销 售商品、提供 劳务2024年预计总金额交是多少",
    ],
    [
        "义乌华鼎锦纶股份有限公司远期结售汇交易金额上限",
    ],
    [
        "天工国际更正原因",
    ]
]

def get_answer(query_input):
    answer, source, debug_info = generate_answer(query_input, enable_q_q_match=False)
    return (answer,
            source,
            debug_info.get("query_parser_info", ""),
            debug_info.get("q_q_match_info", ""),
            debug_info.get("knowledge_qa_knn_recall", ""),
            # debug_info["knowledge_qa_boolean_recall"],
            # debug_info["knowledge_qa_combined_recall"],
            debug_info.get("knowledge_qa_rerank", ""),
            debug_info.get("knowledge_qa_llm", ""))

with gr.Blocks() as demo:
    query_input = gr.Text(label="Query")
    answer_output = gr.Text(label="Anwser", show_label=True)
    sources_output = gr.Text(label="Sources", show_label=True)
    with gr.Accordion("QueryParserDebugInfo", open=False):
        query_parser_debuge_info = gr.JSON()
    with gr.Accordion("QQMatcherDebugInfo", open=False):
        qq_match_debuge_info = gr.JSON()
    with gr.Accordion("KNNRetrieverDebugInfo", open=False):
        knn_retriever_debug_info = gr.JSON()
    # with gr.Accordion("BooleanRetrieverDebugInfo", open=False):
    #     boolean_retriever_debug_info = gr.JSON()
    # with gr.Accordion("CombineRetrieverDebugInfo", open=False):
    #     combine_retriever_debug_info = gr.JSON()
    with gr.Accordion("CrossModelDebugInfo", open=False):
        cross_model_debug_info = gr.JSON()
    with gr.Accordion("LLMDebugInfo", open=False):
        llm_debug_info = gr.JSON()
    answer_btn = gr.Button(value="Answer")
    context = None
    answer_btn.click(get_answer,
              inputs=[query_input],
              outputs=[answer_output,
                       sources_output,
                       query_parser_debuge_info,
                       qq_match_debuge_info,
                       knn_retriever_debug_info,
                       # boolean_retriever_debug_info,
                       # combine_retriever_debug_info,
                       cross_model_debug_info,
                       llm_debug_info])
    url_input = gr.Text(label="Url")
    with gr.Accordion("RawDataDebugInfo", open=False):
        raw_data = gr.JSON()
    check_btn = gr.Button(value="Check")
    check_btn.click(check_data,
              inputs=[url_input],
              outputs=[raw_data])
    gr.Examples(
        examples = text,
        inputs = [query_input],
        fn = generate_answer,
        cache_examples=False,
    )

# load_raw_data()
demo.queue()
demo.launch(server_name="0.0.0.0", share=True, server_port=3306)
