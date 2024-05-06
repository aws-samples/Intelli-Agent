import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import logging
import time
import uuid
import boto3
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from utils.logger_utils import get_logger

logger = get_logger("intention")


# @handle_error
def lambda_handler(event, context):
    embedding_endpoint = os.environ.get('embedding_endpoint')
    region = os.environ.get('region')
    aos_endpoint = os.environ.get('aos_endpoint')
    # index_name = os.environ.get('index_name')
    query = event.get('query')
    index_name = event.get('example_index')
    fewshot_cnt = event.get('fewshot_cnt')
    llm_model_endpoint = os.environ.get('llm_model_endpoint')
    
    logger.info("embedding_endpoint: {}".format(embedding_endpoint))
    logger.info("region:{}".format(region))
    logger.info("aos_endpoint:{}".format(aos_endpoint))
    logger.info("index_name:{}".format(index_name))
    logger.info("fewshot_cnt:{}".format(fewshot_cnt))
    logger.info("llm_model_endpoint:{}".format(llm_model_endpoint))


    # 通过workspace获取检索结果，并根据检索的阈值进行过滤
    q_embedding = get_embedding_from_text(query, embedding_endpoint)
    doc_retriever = CustomDocRetriever.from_endpoints(embedding_model_endpoint=embedding_endpoint,
                                aos_endpoint= aos_endpoint,
                                aos_index=index_name)
    docs_simple = doc_retriever.search_example_by_aos_knn(q_embedding=q_embedding[0], example_index=index_name, sim_threshold=SIMS_THRESHOLD, size=fewshot_cnt)

    #如果没有召回到example，则默认走QA，通过QA阶段的策略去判断，召回内容的是否跟问题相关，如果不相关则走chat
    if not docs_simple:
        answer = {"func":"QA"}
        logger.info(f"Notice: No Intention detected, return default:{json.dumps(answer,ensure_ascii=False)}")
        return answer
    
    # 构造example list
    example_list = [ "<query>{}</query>\n<output>{}</output>".format(doc['query'], json.dumps(doc['detection'], ensure_ascii=False)) for doc in docs_simple ]

    api_schema_list = [ doc['api_schema'] for doc in docs_simple]

    options = set([ doc['detection'] for doc in docs_simple])

    default_ret = {"func":"QA"}

    if len(options) == 1 and len(docs_simple) == fewshot_cnt:
        logger.info("Notice: Only Single latent Intention detected.")
        answer = options.pop()
        ret = default_ret
        try:
            ret = json.loads(answer)
            log_dict = { "answer" : answer, "examples": docs_simple }
            log_dict_str = json.dumps(log_dict, ensure_ascii=False)
            logger.info(log_dict_str)
        except Exception as e:
            logger.info("Fail to parse answer - {}".format(str(answer)))
        return ret

    api_schema_options = set(api_schema_list)
    api_schema_str = "<api_schema>\n{}\n</api_schema>".format(",\n".join(api_schema_options))
    example_list_str = "\n{}\n".format("\n".join(example_list))
    
    parameters = {
        "max_tokens": 1000,
        "stop": ["</output>"],
        "temperature":0.01,
        "top_p":0.95
    }
    
    if llm_model_endpoint.startswith('claude') or llm_model_endpoint.startswith('anthropic'):
        model_id = BEDROCK_LLM_MODELID_LIST.get(llm_model_endpoint, BEDROCK_LLM_MODELID_LIST["claude-v3-sonnet"])
    else:
        model_id = llm_model_endpoint

    llm = get_langchain_llm_model(model_id, parameters, region, llm_stream=False)
    
    prompt_template = create_detect_prompt_templete()
    prefix = """{"func":"""
    prefill = """<query>{query}</query>\n<output>{prefix}""".format(query=query, prefix=prefix)

    prompt = prompt_template.format(api_schemas=api_schema_str, examples=example_list_str)
    msg = format_to_message(query=prompt)
    msg_list = [msg, {"role":"assistant", "content": prefill}]
    ai_reply = invoke_model(llm=llm, prompt=prompt, messages=msg_list)
    final_prompt = json.dumps(msg_list,ensure_ascii=False)
    answer = ai_reply.content
    
    answer = prefix + answer.strip()
    answer = answer.replace('<output>', '')

    log_dict = { "prompt" : final_prompt, "answer" : answer , "examples": docs_simple }
    # log_dict_str = json.dumps(log_dict, ensure_ascii=False)
    logger.info(log_dict)

    # if answer not in options:
    #     answer = intention_counter.most_common(1)[0]
    #     for opt in options:
    #         if opt in answer:
    #             answer = opt
    #             break

    try:
        ret = json.loads(answer)
    except Exception as e:
        logger.info("Fail to detect function, caused by {}".format(str(e)))
    finally:
        ret = ret if ret.get('func') else default_ret
    return ret 

    