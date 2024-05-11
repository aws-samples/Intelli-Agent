import json
import os
import logging
import time
import uuid
import boto3
import json 
import sys
from textwrap import dedent
from functools import partial
from typing import TypedDict,Annotated

from langchain.schema.runnable import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough
)
from langgraph.graph import END, StateGraph

from layer_logic.utils.logger_utils  import get_logger
from layer_logic.utils.lambda_invoke_utils import invoke_with_lambda,invoke_with_handler
from layer_logic.utils.langchain_utils import chain_logger,RunnableParallelAssign,NestUpdateState

logger = get_logger("intention")


# 过滤qq结果
def documents_list_filter(doc_dicts: list[dict], filter_key="score", threshold=-1):
    results = []
    for doc_dict in doc_dicts:
        if doc_dict[filter_key] < threshold:
            continue
        results.append(doc_dict)

    return results


def get_qq_match_chain(state:dict):
    qq_workspace_list = state["qq_workspace_list"]
    config = state["config"]
    trace_infos = state['trace_infos']
    qq_match_threshold = config["retriever_config"]["qq_config"][
        "qq_match_threshold"
    ]
    qq_retriever_top_k = config["retriever_config"]["qq_config"]["retriever_top_k"]

    qq_retriever_results_chain = chain_logger(
        "qq_retriever_lambda",
        RunnableLambda(
                lambda x: invoke_with_lambda(
                    lambda_name="lambda_retriever",
                    event_body= {
                            "type": "qq_aos",
                            "workspace_ids": qq_workspace_list,
                            "query": x['query'],
                            "retriever_top_k": qq_retriever_top_k,
                            "method": "knn"
                        }
                )
        ),
        trace_infos=trace_infos
    )
    
    qq_chain = qq_retriever_results_chain | RunnableLambda(
            partial(documents_list_filter, threshold=qq_match_threshold)
        )
    return qq_chain


def get_aos_intent_recognition_chain(state:dict):
    intention_workspace_list = state["intention_workspace_list"]
    config = state["config"]
    trace_infos = state['trace_infos']

    intention_retriever_top_k = config["intention_config"]["aos_config"]["retriever_top_k"]

    intention_retriever_results_chain = chain_logger(
        "intention_retriever_lambda",
        RunnableLambda(
            lambda x: invoke_with_lambda(
                lambda_name="lambda_retriever",
                event_body= {
                        "type": "qq_aos",
                        "workspace_ids": intention_workspace_list,
                        "query": x['query'],
                        "retriever_top_k": intention_retriever_top_k,
                        "method": "knn"
                    }
            )
        ),
        trace_infos=trace_infos
    )
    
    # 过滤intent
    intention_chain = intention_retriever_results_chain | \
        RunnableLambda(lambda retriever_list: sorted(retriever_list, key=lambda x: x["score"])[-1]["intent"])

    return intention_chain 


def qq_match_and_intent_recognition(state):
    state = state["keys"]
    qq_chain = get_qq_match_chain(state)
    intent_recognition_chain = get_aos_intent_recognition_chain(state)

    log_output_template = dedent("""
        qq_result num: {qq_result_num}
        intent recognition type: {intent_type}
    """)
    qq_and_intention_type_recognition_chain = chain_logger(
        RunnableParallelAssign(
            qq_result=qq_chain,
            intent_type=intent_recognition_chain,
        )
        | RunnablePassthrough.assign(qq_result_num=lambda x: len(x["qq_result"])),
        "qq_and_intention_type_recognition_chain",
        log_output_template=log_output_template,
        # message_id=state["message_id"],
    )

    _state = qq_and_intention_type_recognition_chain.invoke(state)
    state.update(_state)

# @handle_error
def lambda_handler(event, context=None):
    # embedding_endpoint = os.environ.get('embedding_endpoint')
    # region = os.environ.get('region')
    # aos_endpoint = os.environ.get('aos_endpoint')
    # # index_name = os.environ.get('index_name')
    # query = event.get('query')
    # index_name = event.get('example_index')
    # fewshot_cnt = event.get('fewshot_cnt')
    # llm_model_endpoint = os.environ.get('llm_model_endpoint')

    event_body = json.loads(event["body"])
    state:dict = event_body['state']
    logger.info(f'state: {json.dumps(state,ensure_ascii=False,indent=2)}')

    workflow = StateGraph(NestUpdateState)

    workflow.add_node('qq_match_and_intent_recognition',qq_match_and_intent_recognition)
    workflow.set_entry_point('qq_match_and_intent_recognition')
    workflow.set_finish_point('qq_match_and_intent_recognition')

    app = workflow.compile()

    output = app.invoke(state)
    
    state.update(output)

    return state

    # logger.info("embedding_endpoint: {}".format(embedding_endpoint))
    # logger.info("region:{}".format(region))
    # logger.info("aos_endpoint:{}".format(aos_endpoint))
    # logger.info("index_name:{}".format(index_name))
    # logger.info("fewshot_cnt:{}".format(fewshot_cnt))
    # logger.info("llm_model_endpoint:{}".format(llm_model_endpoint))
    
    # qq match

    # intent recognition
    
    # TODO 通过workspace获取检索结果，并根据检索的阈值进行过滤
    # q_embedding = get_embedding_from_text(query, embedding_endpoint)
    # doc_retriever = CustomDocRetriever.from_endpoints(embedding_model_endpoint=embedding_endpoint,
    #                             aos_endpoint= aos_endpoint,
    #                             aos_index=index_name)
    # docs_simple = doc_retriever.search_example_by_aos_knn(q_embedding=q_embedding[0], example_index=index_name, sim_threshold=SIMS_THRESHOLD, size=fewshot_cnt)

    #如果没有召回到example，则默认走QA，通过QA阶段的策略去判断，召回内容的是否跟问题相关，如果不相关则走chat
    # if not docs_simple:
    #     answer = {"func":"QA"}
    #     logger.info(f"Notice: No Intention detected, return default:{json.dumps(answer,ensure_ascii=False)}")
    #     return answer
    
    # # 构造example list
    # example_list = [ "<query>{}</query>\n<output>{}</output>".format(doc['query'], json.dumps(doc['detection'], ensure_ascii=False)) for doc in docs_simple ]

    # api_schema_list = [ doc['api_schema'] for doc in docs_simple]

    # options = set([ doc['detection'] for doc in docs_simple])

    # default_ret = {"func":"QA"}

    # if len(options) == 1 and len(docs_simple) == fewshot_cnt:
    #     logger.info("Notice: Only Single latent Intention detected.")
    #     answer = options.pop()
    #     ret = default_ret
    #     try:
    #         ret = json.loads(answer)
    #         log_dict = { "answer" : answer, "examples": docs_simple }
    #         log_dict_str = json.dumps(log_dict, ensure_ascii=False)
    #         logger.info(log_dict_str)
    #     except Exception as e:
    #         logger.info("Fail to parse answer - {}".format(str(answer)))
    #     return ret

    # api_schema_options = set(api_schema_list)
    # api_schema_str = "<api_schema>\n{}\n</api_schema>".format(",\n".join(api_schema_options))
    # example_list_str = "\n{}\n".format("\n".join(example_list))
    
    # parameters = {
    #     "max_tokens": 1000,
    #     "stop": ["</output>"],
    #     "temperature":0.01,
    #     "top_p":0.95
    # }
    
    # if llm_model_endpoint.startswith('claude') or llm_model_endpoint.startswith('anthropic'):
    #     model_id = BEDROCK_LLM_MODELID_LIST.get(llm_model_endpoint, BEDROCK_LLM_MODELID_LIST["claude-v3-sonnet"])
    # else:
    #     model_id = llm_model_endpoint

    # llm = get_langchain_llm_model(model_id, parameters, region, llm_stream=False)
    
    # prompt_template = create_detect_prompt_templete()
    # prefix = """{"func":"""
    # prefill = """<query>{query}</query>\n<output>{prefix}""".format(query=query, prefix=prefix)

    # prompt = prompt_template.format(api_schemas=api_schema_str, examples=example_list_str)
    # msg = format_to_message(query=prompt)
    # msg_list = [msg, {"role":"assistant", "content": prefill}]
    # ai_reply = invoke_model(llm=llm, prompt=prompt, messages=msg_list)
    # final_prompt = json.dumps(msg_list,ensure_ascii=False)
    # answer = ai_reply.content
    
    # answer = prefix + answer.strip()
    # answer = answer.replace('<output>', '')

    # log_dict = { "prompt" : final_prompt, "answer" : answer , "examples": docs_simple }
    # # log_dict_str = json.dumps(log_dict, ensure_ascii=False)
    # logger.info(log_dict)

    # if answer not in options:
    #     answer = intention_counter.most_common(1)[0]
    #     for opt in options:
    #         if opt in answer:
    #             answer = opt
    #             break

    # try:
    #     ret = json.loads(answer)
    # except Exception as e:
    #     logger.info("Fail to detect function, caused by {}".format(str(e)))
    # finally:
    #     ret = ret if ret.get('func') else default_ret
    # return ret 


