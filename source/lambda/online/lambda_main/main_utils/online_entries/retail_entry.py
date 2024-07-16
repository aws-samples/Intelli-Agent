import json
import re
import random
from datetime import datetime 
from textwrap import dedent
from typing import TypedDict,Any,Annotated
import validators
from langgraph.graph import StateGraph,END
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,node_monitor_wrapper
from common_logic.common_utils.python_utils import update_nest_dict,add_messages
from common_logic.common_utils.constant import (
    LLMTaskType,
    ToolRuningMode,
    SceneType
)

from functions.lambda_retail_tools.lambda_product_information_search.product_information_search import goods_dict

from lambda_main.main_utils.parse_config import parse_retail_entry_config
from common_logic.common_utils.lambda_invoke_utils import send_trace,is_running_local
from common_logic.common_utils.logger_utils import get_logger
from common_logic.common_utils.serialization_utils import JSONEncoder
from common_logic.common_utils.s3_utils import download_file_from_s3,check_local_folder
from lambda_main.main_utils.online_entries.agent_base import build_agent_graph,tool_execution
from functions import get_tool_by_name,init_retail_tools

order_info_path = "/tmp/functions/retail_tools/lambda_order_info/order_info.json"
check_local_folder(order_info_path)
download_file_from_s3("aws-chatbot-knowledge-base-test", "retail_json/order_info.json", order_info_path)
order_dict = json.load(open(order_info_path))

logger = get_logger('retail_entry')

init_retail_tools()
# goods_info_tag = "商品信息"

class ChatbotState(TypedDict):
    chatbot_config: dict # chatbot config
    query: str 
    create_time: str 
    ws_connection_id: str 
    stream: bool 
    query_rewrite: str = None  # query rewrite ret
    intent_type: str = None # intent
    intention_fewshot_examples: list
    trace_infos: Annotated[list[str],add_messages]
    message_id: str = None
    chat_history: Annotated[list[dict],add_messages]
    agent_tool_history: Annotated[list[dict],add_messages]
    current_function_calls: list[str]
    current_tool_execute_res: dict
    debug_infos: Annotated[dict,update_nest_dict]
    answer: Any  # final answer
    current_monitor_infos: str 
    extra_response: Annotated[dict,update_nest_dict]
    contexts: str = None
    current_intent_tools: list #
    current_agent_intent_type: str = None
    current_tool_calls:list 
    # current_agent_tools_def: list[dict]
    # current_agent_model_id: str
    current_agent_output: dict
    parse_tool_calling_ok: bool
    query_rule_classification: str
    goods_info: None
    human_goods_info: None
    agent_llm_type: str
    query_rewrite_llm_type: str
    agent_repeated_call_limit: int # agent recursion limit
    agent_current_call_number: int
    enable_trace: bool
    goods_info_tag = "商品信息"

####################
# nodes in lambdas #
####################

@node_monitor_wrapper
def query_preprocess(state: ChatbotState):
    output:str = invoke_lambda(
        event_body={**state,"chat_history":[]},
        lambda_name="Online_Query_Preprocess",
        lambda_module_path="lambda_query_preprocess.query_preprocess",
        handler_name="lambda_handler"
    )
    state['extra_response']['query_rewrite'] = output
    send_trace(f"\n\n **query_rewrite:** \n{output}")
    return {
            "query_rewrite":output,
            "current_monitor_infos":f"query_rewrite: {output}"
        }

@node_monitor_wrapper
def intention_detection(state: ChatbotState):
    intention_fewshot_examples = invoke_lambda(
        lambda_module_path='lambda_intention_detection.intention',
        lambda_name="Online_Intention_Detection",
        handler_name="lambda_handler",
        event_body=state 
    )
    state['extra_response']['intention_fewshot_examples'] = intention_fewshot_examples

    # send trace
    send_trace(f"\n\nintention retrieved:\n{json.dumps(intention_fewshot_examples,ensure_ascii=False,indent=2)}", state["stream"], state["ws_connection_id"])
    current_intent_tools:list[str] = list(set([e['intent'] for e in intention_fewshot_examples]))
    return {
        "intention_fewshot_examples": intention_fewshot_examples,
        "current_intent_tools": current_intent_tools,
        "intent_type": "other"
        }

@node_monitor_wrapper
def agent(state: ChatbotState):
    goods_info = state.get('goods_info',None) or ""
    agent_tool_history = state.get('agent_tool_history',"")
    if agent_tool_history and hasattr(agent_tool_history[-1],'additional_kwargs'):
        search_result = agent_tool_history[-1]['additional_kwargs']['original'][0].get('search_result',1)
        if search_result == 0:
            context = agent_tool_history[-1]['additional_kwargs']['original'][0].get('result',"")
            system_prompt = ("你是安踏的客服助理，正在帮消费者解答问题，消费者提出的问题大多是属于商品的质量和物流规则。context列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
                            "<context>\n"
                            f"{context}\n"
                            "</context>"
                            "你需要按照下面的guidelines对消费者的问题进行回答:\n"
                            "<guidelines>\n"
                            " - 回答内容为一句话，言简意赅。\n"
                            " - 如果问题与context内容不相关，就不要采用。\n"
                            " - 消费者的问题里面可能包含口语化的表达，比如鞋子开胶的意思是用胶黏合的鞋体裂开。这和胶丝遗留没有关系。\n"
                            ' - 如果问题涉及到订单号，请回复: "请稍等，正在帮您查询订单。"'
                            "</guidelines>"
                            )
            query = state['query']
            # print('llm config',state['chatbot_config']['rag_product_aftersales_config']['llm_config'])
            output:str = invoke_lambda(
                lambda_name='Online_LLM_Generate',
                lambda_module_path="lambda_llm_generate.llm_generate",
                handler_name='lambda_handler',
                event_body={
                    "llm_config": {
                        **state['chatbot_config']['rag_product_aftersales_config']['llm_config'], 
                        "system_prompt": system_prompt,
                          "intent_type": LLMTaskType.CHAT
                        },
                    "llm_input": { "query": query, "chat_history": state['chat_history']}
                    }
            )
            agent_current_call_number = state['agent_current_call_number'] + 1
            current_agent_output = {}
            current_agent_output['agent_output'] = {}
            current_agent_output['agent_output']['function_calls'] = []
            current_agent_output['agent_output']['content'] = output
            current_agent_output['current_agent_model_id'] = "qwen2-72B-instruct"
            current_agent_output['current_agent_tools_def'] = []
            return {
                "current_agent_output": current_agent_output,
                "agent_current_call_number": agent_current_call_number
            }

    # deal with once tool calling
    if state['agent_repeated_call_validation'] and state['parse_tool_calling_ok'] and state['agent_tool_history']:
        tool_execute_res = state['agent_tool_history'][-1]['additional_kwargs']['raw_tool_call_results'][0]
        tool_name = tool_execute_res['name']
        output = tool_execute_res['output']
        tool = get_tool_by_name(tool_name,scene=SceneType.RETAIL)
        if tool.running_mode == ToolRuningMode.ONCE:
            send_trace("once tool")
            return {
                "answer": str(output['result']),
                "is_current_tool_calling_once": True
            }
    
    other_chain_kwargs = {
                "goods_info": goods_info,
                "create_time": state['create_time'],
                "agent_current_call_number":state['agent_current_call_number']
        }
    
    response = app_agent.invoke({
        **state,
        "other_chain_kwargs":other_chain_kwargs
    })
    return response
    
    # current_agent_output:dict = invoke_lambda(
    #     event_body={
    #         **state,
    #         "other_chain_kwargs":{
    #             "goods_info": goods_info,
    #             "create_time": state['create_time'],
    #             "agent_current_call_number":state['agent_current_call_number']
    #             }
    #     },
    #     lambda_name="Online_Agent",
    #     lambda_module_path="lambda_agent.agent",
    #     handler_name="lambda_handler"
    # )
    # agent_current_call_number = state['agent_current_call_number'] + 1
    # send_trace(f"\n\n**current_agent_output:** \n{json.dumps(current_agent_output['agent_output'],ensure_ascii=False,indent=2)}\n\n **agent_current_call_number:** {agent_current_call_number}", state["stream"], state["ws_connection_id"])
    # return {
    #     "current_agent_output": current_agent_output,
    #     "agent_current_call_number": agent_current_call_number
    # }

# @node_monitor_wrapper
# def tool_execute_lambda(state: ChatbotState):
#     """executor lambda
#     Args:
#         state (NestUpdateState): _description_

#     Returns:
#         _type_: _description_
#     """
#     tool_calls = state['current_tool_calls']
#     assert len(tool_calls) == 1, tool_calls
#     tool_call_results = []
#     for tool_call in tool_calls:
#         tool_name = tool_call["name"]
#         tool_kwargs = tool_call['kwargs']
#         # call tool
#         output = invoke_lambda(
#             event_body = {
#                 "tool_name":tool_name,
#                 "state":state,
#                 "kwargs":tool_kwargs
#                 },
#             lambda_name="Online_Tool_Execute",
#             lambda_module_path="functions.lambda_tool",
#             handler_name="lambda_handler"   
#         )
#         tool_call_results.append({
#             "name": tool_name,
#             "output": output,
#             "kwargs": tool_call['kwargs'],
#             "model_id": tool_call['model_id']
#         })
    
#     output = format_tool_call_results(tool_call['model_id'],tool_call_results)
#     send_trace(f'**tool_execute_res:** \n{output["tool_message"]["content"]}')
#     return {
#         "agent_tool_history": [output['tool_message']]
#         }


# @node_monitor_wrapper
# def rag_daily_reception_retriever_lambda(state: ChatbotState):
#     # call retriever
#     retriever_params = state["chatbot_config"]["rag_daily_reception_config"]['retriever_config']
#     retriever_params["query"] = state["query"]
#     output:str = invoke_lambda(
#         event_body=retriever_params,
#         lambda_name="Online_Function_Retriever",
#         lambda_module_path="functions.lambda_retriever.retriever",
#         handler_name="lambda_handler"
#     )
#     contexts = [doc['page_content'] for doc in output['result']['docs']]
#     context = "\n\n".join(contexts)
#     send_trace(f'**rag_goods_exchange_retriever** {context}', state["stream"], state["ws_connection_id"])
#     return {"contexts": contexts}

# @node_monitor_wrapper
# def rag_daily_reception_llm_lambda(state:ChatbotState):
#     context = "\n\n".join(state['contexts'])
#     system_prompt = (f"你是安踏的客服助理，正在帮用户解答问题，客户提出的问题大多是属于日常接待类别，你需要按照下面的guidelines进行回复:\n"
#                     "<guidelines>\n"
#                     " - 回复内容需要展现出礼貌。回答内容为一句话，言简意赅。\n"
#                     " - 使用中文回答。\n"
#                     "</guidelines>\n"
#                     "下面列举了一些具体的场景下的回复，你可以结合用户的问题进行参考:\n"
#                     "<context>\n"
#                     f"{context}\n"
#                     "</context>"
#                 )
    
#     output:str = invoke_lambda(
#         lambda_name='Online_LLM_Generate',
#         lambda_module_path="lambda_llm_generate.llm_generate",
#         handler_name='lambda_handler',
#         event_body={
#             "llm_config": {
#                 **state['chatbot_config']['rag_daily_reception_config']['llm_config'], 
#                 "system_prompt": system_prompt,
#                 "intent_type": LLMTaskType.CHAT},
#             "llm_input": {"query": state['query'], "chat_history": state['chat_history']}
#             }
#         )
#     return {"answer": output}

# @node_monitor_wrapper
# def rag_goods_exchange_retriever_lambda(state: ChatbotState):
#     # call retriever
#     retriever_params = state["chatbot_config"]["rag_goods_exchange_config"]['retriever_config']
#     retriever_params["query"] = state["query"]
#     output:str = invoke_lambda(
#         event_body=retriever_params,
#         lambda_name="Online_Function_Retriever",
#         lambda_module_path="functions.lambda_retriever.retriever",
#         handler_name="lambda_handler"
#     )
#     contexts = [doc['page_content'] for doc in output['result']['docs']]

#     context = "\n\n".join(contexts)
#     send_trace(f'**rag_goods_exchange_retriever** {context}', state["stream"], state["ws_connection_id"])
#     return {"contexts": contexts}


# @node_monitor_wrapper
# def rag_goods_exchange_llm_lambda(state:ChatbotState):
#     context = "\n\n".join(state['contexts'])
#     system_prompt = (f"你是安踏的客服助理，正在帮用户解答问题，客户提出的问题大多是属于商品退换货范畴，你需要按照下面的guidelines进行回复:\n"
#                     "<guidelines>\n"
#                     " - 回复内容需要展现出礼貌。回答内容为一句话，言简意赅。\n"
#                     " - 使用中文回答。\n"
#                     "</guidelines>\n"
#                     "下面列举了一些具体的场景下的回复，你可以结合用户的问题进行参考回答:\n"
#                     "<context>\n"
#                     f"{context}\n"
#                     "</context>\n"
#                 )
    
#     output:str = invoke_lambda(
#         lambda_name='Online_LLM_Generate',
#         lambda_module_path="lambda_llm_generate.llm_generate",
#         handler_name='lambda_handler',
#         event_body={
#             "llm_config": {
#                 **state['chatbot_config']['rag_goods_exchange_config']['llm_config'],
#                 "system_prompt":system_prompt,
#                 "intent_type": LLMTaskType.CHAT},
#             "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
#             }
#         )
#     return {"answer": output}

# @node_monitor_wrapper
# def rag_product_aftersales_retriever_lambda(state: ChatbotState):
#     # call retriever
#     recent_tool_calling:list[dict] = state['current_tool_calls'][0]
#     if "shop" in recent_tool_calling['kwargs'] and recent_tool_calling['kwargs']['shop'] != "tianmao":
#         contexts = ["顾客不是在天猫购买的商品，请他咨询其他商家"]
#         return {"contexts": contexts}
#     retriever_params = state["chatbot_config"]["rag_product_aftersales_config"]["retriever_config"]
#     retriever_params["query"] = state["query"]
#     output:str = invoke_lambda(
#         event_body=retriever_params,
#         lambda_name="Online_Function_Retriever",
#         lambda_module_path="functions.lambda_retriever.retriever",
#         handler_name="lambda_handler"
#     )
#     contexts = [doc['page_content'] for doc in output['result']['docs']]

#     context = "\n\n".join(contexts)
#     send_trace(f'**rag_product_aftersales_retriever** {context}', state["stream"], state["ws_connection_id"])
#     return {"contexts": contexts}

# @node_monitor_wrapper
# def rag_product_aftersales_llm_lambda(state:ChatbotState):
#     create_time = state.get('create_time', None)
#     goods_id = state.get('chatbot_config').get('goods_id', 757492962957)
#     try:
#         create_datetime_object = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S.%f')
#     except Exception as e:
#         create_datetime_object = datetime.now()
#         print(f"create_time: {create_time} is not valid, use current time instead.")
#     create_time_str = create_datetime_object.strftime('%Y-%m-%d')
#     # TODO: fix received time format
#     received_time = order_dict.get(str(goods_id), {}).get("received_time", "2023/9/129:03:13")
#     order_time = " ".join([received_time[:9], received_time[9:]])
#     try:
#         order_date_str = datetime.strptime(order_time, '%Y/%m/%d %H:%M:%S').strftime('%Y-%m-%d')
#         receive_elapsed_days = (create_datetime_object - datetime.strptime(order_date_str, '%Y-%m-%d')).days
#         receive_elapsed_months = receive_elapsed_days // 30
#     except Exception as e:
#         order_date_str = "2023-9-12"
#         receive_elapsed_months = 6
#     context = "\n\n".join(state['contexts'])
#     system_prompt = (f"你是安踏的客服助理，正在帮消费者解答问题，消费者提出的问题大多是属于商品的质量和物流规则。context列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
#                     f"客户咨询的问题所对应的订单日期为{order_date_str}。\n"
#                     f"当前时间{create_time_str}\n"
#                     f"客户收到商品已经超过{receive_elapsed_months}个月\n"
#                     "<context>\n"
#                     f"{context}\n"
#                     "</context>\n"
#                     "你需要按照下面的guidelines对消费者的问题进行回答:\n"
#                     "<guidelines>\n"
#                     " - 回答内容为一句话，言简意赅。\n"
#                     " - 如果问题与context内容不相关，就不要采用。\n"
#                     " - 消费者的问题里面可能包含口语化的表达，比如鞋子开胶的意思是用胶黏合的鞋体裂开。这和胶丝遗留没有关系\n"
#                     " - 洗涤后出现问题也属于质量问题\n"
#                     " - 消费者的回复不够清晰的时候，直接回复: 不知道刚才给您的建议是否有帮助？。不要有额外补充\n"
#                     " - 如果客户问到质量相关问题，请根据前面的订单信息和三包规则，确定是否超出三包期限，如果超出三包期限请告知消费者无法处理，如果在三包期限内请按照三包要求处理，并安抚。\n"
#                     "</guidelines>\n"
#                     )
#     # print('llm config',state['chatbot_config']['rag_product_aftersales_config']['llm_config'])
#     output:str = invoke_lambda(
#         lambda_name='Online_LLM_Generate',
#         lambda_module_path="lambda_llm_generate.llm_generate",
#         handler_name='lambda_handler',
#         event_body={
#             "llm_config": {
#                 **state['chatbot_config']['rag_product_aftersales_config']['llm_config'], 
#                 "system_prompt":system_prompt,
#                 "intent_type": LLMTaskType.CHAT
#             },
#             "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
#             }
#         )
#     return {"answer": output}

# @node_monitor_wrapper
# def rag_customer_complain_retriever_lambda(state: ChatbotState):
#     # call retriever
#     retriever_params = state["chatbot_config"]["rag_customer_complain_config"]["retriever_config"]
#     retriever_params["query"] = state["query"]
#     output:str = invoke_lambda(
#         event_body=retriever_params,
#         lambda_name="Online_Function_Retriever",
#         lambda_module_path="functions.lambda_retriever.retriever",
#         handler_name="lambda_handler"
#     )
#     contexts = [doc['page_content'] for doc in output['result']['docs']]

#     context = "\n\n".join(contexts)
#     send_trace(f'**rag_customer_complain_retriever** {context}', state["stream"], state["ws_connection_id"])
#     return {"contexts": contexts}

# @node_monitor_wrapper
# def rag_customer_complain_llm_lambda(state:ChatbotState):
#     context = "\n\n".join(state['contexts'])
#     # prompt = dedent(f"""你是安踏的客服助理，正在处理有关于客户抱怨的问题，这些问题有关于商品质量等方面，需要你按照下面的guidelines进行回复:
#     system_prompt = ("你是安踏的客服助理，正在处理有关于消费者抱怨的问题。context列举了一些可能和客户问题有关的具体场景及回复，你可以进行参考:\n"
#                     "<context>\n"
#                     f"{context}\n"
#                     "</context>\n"
#                     "需要你按照下面的guidelines进行回复:\n"
#                     "<guidelines>\n"
#                     " - 回答内容为一句话，言简意赅。\n"
#                     " - 尽量安抚客户情绪。\n"
#                     " - 直接回答，不要说\"亲爱的顾客，您好\"\n"
#                     "</guidelines>\n"
#                     )
#     output:str = invoke_lambda(
#         lambda_name='Online_LLM_Generate',
#         lambda_module_path="lambda_llm_generate.llm_generate",
#         handler_name='lambda_handler',
#         event_body={
#             "llm_config": {
#                 **state['chatbot_config']['rag_customer_complain_config']['llm_config'],
#                 "system_prompt":system_prompt,
#                 "intent_type": LLMTaskType.CHAT},
#             "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
#             }
#         )
#     return {"answer": output}

# @node_monitor_wrapper
# def rag_promotion_retriever_lambda(state: ChatbotState):
#     # call retriever
#     retriever_params = state["chatbot_config"]["rag_promotion_config"]["retriever_config"]
#     retriever_params["query"] = state["query"]
#     output:str = invoke_lambda(
#         event_body=retriever_params,
#         lambda_name="Online_Function_Retriever",
#         lambda_module_path="functions.lambda_retriever.retriever",
#         handler_name="lambda_handler"
#     )
#     contexts = [doc['page_content'] for doc in output['result']['docs']]

#     context = "\n\n".join(contexts)
#     send_trace(f'**rag_promotion_retriever** {context}', state["stream"], state["ws_connection_id"])
#     return {"contexts": contexts}

# @node_monitor_wrapper
# def rag_promotion_llm_lambda(state:ChatbotState):
#     context = "\n\n".join(state['contexts'])

#     system_prompt = ("你是安踏的客服助理，正在帮消费者解答有关于商品促销的问题，这些问题是有关于积分、奖品、奖励等方面。\n"
#                      "context列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
#                     f"<context>\n{context}\n</context>\n"
#                     "你需要按照下面的guidelines对消费者的问题进行回答:\n"
#                     "<guidelines>\n"
#                     " - 回答内容为一句话，言简意赅。\n"
#                     " - 如果问题与context内容不相关，就不要采用。\n"
#                     " - 使用中文进行回答。\n"
#                     "</guidelines>"
#     )
   
#     output:str = invoke_lambda(
#         lambda_name='Online_LLM_Generate',
#         lambda_module_path="lambda_llm_generate.llm_generate",
#         handler_name='lambda_handler',
#         event_body={
#             "llm_config": {
#                 **state['chatbot_config']['rag_promotion_config']['llm_config'],
#                 "system_prompt":system_prompt,
#                 "intent_type": LLMTaskType.CHAT},
#             "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
#             }
#         )
#     return {"answer": output}



@node_monitor_wrapper
def final_rag_retriever_lambda(state: ChatbotState):
    # call retriever
    retriever_params = state["chatbot_config"]["final_rag_retriever"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n".join(contexts)
    send_trace(f'**final_rag_retriever** {context}')
    return {"contexts": contexts}

@node_monitor_wrapper
def final_rag_llm_lambda(state:ChatbotState):
    context = "\n\n".join(state['contexts'])
    system_prompt = ("你是安踏的客服助理，正在帮消费者解答售前或者售后的问题。 <context> 中列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>\n"
                    "你需要按照下面的guidelines对消费者的问题进行回答:\n"
                    "<guidelines>\n"
                    " - 回答内容为一句话，言简意赅。\n"
                    " - 如果问题与context内容不相关，就不要采用。\n"
                    "</guidelines>\n"
                )
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['final_rag_retriever']['llm_config'],
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": { "query": state["query"], "chat_history": state['chat_history']}
            }
        )
    return {"answer": output}


# def transfer_reply(state:ChatbotState):
#     return {"answer": "您好,我是安踏官方客服,很高兴为您服务。请问您有什么需要帮助的吗?"}


# def give_rhetorical_question(state:ChatbotState):
#     recent_tool_calling:list[dict] = state['current_tool_calls'][0]
#     return {"answer": recent_tool_calling['kwargs']['question']}


# def give_final_response(state:ChatbotState):
#     recent_tool_calling:list[dict] = state['current_tool_calls'][0]
#     return {"answer": recent_tool_calling['kwargs']['response']}

# def rule_url_reply(state:ChatbotState):
#     state["extra_response"]["current_agent_intent_type"] = "rule reply"
#     if state['query'].endswith(('.jpg','.png')):
#         answer = random.choice([
#             "收到，亲。请问我们可以怎么为您效劳呢？",
#             "您好，请问有什么需要帮助的吗？"
#         ])
#         return {"answer": answer}
#     # product information
#     r = re.findall(r"item.htm\?id=(.*)",state['query'])
#     if r:
#         goods_id = r[0]
#     else:
#         goods_id = 0
#     if goods_id in goods_dict:
#         # call llm to make summary of goods info
#         human_goods_info = state['human_goods_info']
#         output = f"您好，该商品的特点是:\n{human_goods_info}"
#         if human_goods_info:
#             system_prompt = (f"你是安踏的客服助理，当前用户对下面的商品感兴趣:\n"
#                         f"<{goods_info_tag}>\n{human_goods_info}\n</{goods_info_tag}>\n"
#                         "请你结合商品的基础信息，特别是卖点信息返回一句推荐语。"
#                     )
#             output:str = invoke_lambda(
#                 lambda_name='Online_LLM_Generate',
#                 lambda_module_path="lambda_llm_generate.llm_generate",
#                 handler_name='lambda_handler',
#                 event_body={
#                     "llm_config": {
#                         **state['chatbot_config']['rag_daily_reception_config']['llm_config'], 
#                         "system_prompt": system_prompt,
#                         "intent_type": LLMTaskType.CHAT},
#                     "llm_input": {"query": state['query'], "chat_history": state['chat_history']}
#                         }
#                     )
         
#         return {"answer":output}
    
#     return {"answer":"您好"}

def rule_number_reply(state:ChatbotState):
    state["extra_response"]["current_agent_intent_type"] = "rule reply"
    return {"answer":"收到订单信息"}


def final_results_preparation(state: ChatbotState):
    return {"answer": state['answer']}

# @node_monitor_wrapper
# def tools_choose_and_results_generation(state: ChatbotState):
#     # check once tool calling
#     current_agent_output:dict = invoke_lambda(
#         event_body={
#             **state,
#             # "other_chain_kwargs": {"system_prompt": get_common_system_prompt()}
#             },
#         lambda_name="Online_Agent",
#         lambda_module_path="lambda_agent.agent",
#         handler_name="lambda_handler",
   
#     )
#     agent_current_call_number = state['agent_current_call_number'] + 1
#     agent_repeated_call_validation = state['agent_current_call_number'] < state['agent_repeated_call_limit']

#     send_trace(f"\n\n**current_agent_output:** \n{json.dumps(current_agent_output['agent_output'],ensure_ascii=False,indent=2)}\n\n **agent_current_call_number:** {agent_current_call_number}", state["stream"], state["ws_connection_id"])
#     return {
#         "current_agent_output": current_agent_output,
#         "agent_current_call_number": agent_current_call_number,
#         "agent_repeated_call_validation": agent_repeated_call_validation
#     }


################
# define edges #
################

def query_route(state:dict):
    # check if rule reply
    query = state['query']
    is_all_url = True
    for token in query.split():
        if not validators.url(token):
            is_all_url = False
    if is_all_url:
        return "url"
    if query.isnumeric() and len(query)>=8:
        return "number"
    else:
        return "continue"

def intent_route(state:dict):
    return state['intent_type']

# def agent_route(state:dict):
#     parse_tool_calling_ok = state['parse_tool_calling_ok']
#     if not parse_tool_calling_ok:
#         if state['agent_current_call_number'] >= state['agent_repeated_call_limit']:
#             send_trace(f"Reach the agent recursion limit: {state['agent_repeated_call_limit']}, route to final rag")
#             return 'final rag'
#         return 'invalid tool calling'
    
#     recent_tool_calls:list[dict] = state['current_tool_calls']
    
#     recent_tool_call = recent_tool_calls[0]

#     recent_tool_name = recent_tool_call['name']

#     if recent_tool_name in ['comfort', 'transfer']:
#         return recent_tool_name
    
#     if recent_tool_call['name'] == "give_rhetorical_question":
#         return "rhetorical question"
    
#     if recent_tool_call['name'] == "goods_exchange":
#         return "goods exchange"
    
#     if recent_tool_call['name'] == "daily_reception":
#         return "daily reception"

#     if recent_tool_call['name'] == "rule_response":
#         return "rule response"

#     if recent_tool_call['name'] == 'product_logistics':
#         return "product aftersales"

#     if recent_tool_call['name'] == 'product_quality':
#         return "product aftersales"

#     if recent_tool_call['name'] == 'goods_storage':
#         return "product aftersales"

#     if recent_tool_call['name'] == 'customer_complain':
#         return "customer complain"

#     if recent_tool_call['name'] == 'promotion':
#         return "promotion"
    
#     if recent_tool_call['name'] == "give_final_response":
#         return "give final response"

#     if state['agent_current_call_number'] >= state['agent_repeated_call_limit']:
#         send_trace(f"Reach the agent recursion limit: {state['agent_repeated_call_limit']}, route to final rag")
#         return 'final rag'

#     return "continue"


def agent_route(state: dict):
    if state.get("is_current_tool_calling_once",False):
        return "no need tool calling"
    
    state["agent_repeated_call_validation"] = state['agent_current_call_number'] < state['agent_repeated_call_limit']

    if state["agent_repeated_call_validation"]:
        return "valid tool calling"
    else:
        # TODO give final strategy
        raise 'final rag'

     
#############################
# define whole online graph #
#############################

app_agent = None

def build_graph():
    workflow = StateGraph(ChatbotState)
    # add all nodes
    workflow.add_node("query_preprocess", query_preprocess)
    workflow.add_node("intention_detection", intention_detection)
    workflow.add_node("agent", agent)
    workflow.add_node("tool_execute", tool_execution)
    # workflow.add_node("transfer_reply", transfer_reply)
    # workflow.add_node("give_rhetorical_question",give_rhetorical_question)
    # workflow.add_node("give_final_response",give_final_response)
    # workflow.add_node("give_response_wo_tool",give_response_without_any_tool)
    # workflow.add_node("parse_tool_calling",parse_tool_calling)
    # 
    # workflow.add_node("rag_daily_reception_retriever",rag_daily_reception_retriever_lambda)
    # workflow.add_node("rag_daily_reception_llm",rag_daily_reception_llm_lambda)
    # workflow.add_node("rag_goods_exchange_retriever",rag_goods_exchange_retriever_lambda)
    # workflow.add_node("rag_goods_exchange_llm",rag_goods_exchange_llm_lambda)
    # workflow.add_node("rag_product_aftersales_retriever",rag_product_aftersales_retriever_lambda)
    # workflow.add_node("rag_product_aftersales_llm",rag_product_aftersales_llm_lambda)
    # workflow.add_node("rag_customer_complain_retriever",rag_customer_complain_retriever_lambda)
    # workflow.add_node("rag_customer_complain_llm",rag_customer_complain_llm_lambda)
    # workflow.add_node("rule_url_reply",rule_url_reply)
    workflow.add_node("rule_number_reply",rule_number_reply)
    # workflow.add_node("rag_promotion_retriever",rag_promotion_retriever_lambda)
    # workflow.add_node("rag_promotion_llm",rag_promotion_llm_lambda)
    workflow.add_node("final_rag_retriever",final_rag_retriever_lambda)
    workflow.add_node("final_rag_llm",final_rag_llm_lambda)

    workflow.add_node("final_results_preparation", final_results_preparation)

    # add all edges
    workflow.set_entry_point("query_preprocess")
    # workflow.add_edge("query_preprocess_lambda","intention_detection_lambda")
    workflow.add_edge("intention_detection","agent")
    workflow.add_edge("tool_execute","agent")
    # workflow.add_edge("agent",'parse_tool_calling')
    # workflow.add_edge("rag_daily_reception_retriever","rag_daily_reception_llm")
    # workflow.add_edge('rag_goods_exchange_retriever',"rag_goods_exchange_llm")
    # workflow.add_edge('rag_product_aftersales_retriever',"rag_product_aftersales_llm")
    # workflow.add_edge('rag_customer_complain_retriever',"rag_customer_complain_llm")
    # workflow.add_edge('rag_promotion_retriever',"rag_promotion_llm")
    workflow.add_edge('final_rag_retriever',"final_rag_llm")
    
    # end
    # workflow.add_edge("transfer_reply",END)
    # workflow.add_edge("give_rhetorical_question",END)
    # workflow.add_edge("give_response_wo_tool",END)
    # workflow.add_edge("rag_daily_reception_llm",END)
    # workflow.add_edge("rag_goods_exchange_llm",END)
    # workflow.add_edge("rag_product_aftersales_llm",END)
    # workflow.add_edge("rag_customer_complain_llm",END)
    # workflow.add_edge('rule_url_reply',END)
    workflow.add_edge('rule_number_reply',END)
    # workflow.add_edge("rag_promotion_llm",END)
    # workflow.add_edge("give_final_response",END)
    workflow.add_edge("final_rag_llm",END)

    # temporal add edges for ending logic
    # add conditional edges

    workflow.add_conditional_edges(
        "query_preprocess_lambda",
        query_route,
        {
           "url":  "rule_url_reply",
           "number": "rule_number_reply",
           "continue": "intention_detection_lambda"
        }
    )

    workflow.add_conditional_edges(
        "parse_tool_calling",
        agent_route,
        {
            "invalid tool calling": "agent_lambda",
            # "rhetorical question": "give_rhetorical_question",
            # "transfer": "transfer_reply",
            # "goods exchange": "rag_goods_exchange_retriever",
            # "daily reception": "rag_daily_reception_retriever",
            # "product aftersales": "rag_product_aftersales_retriever",
            # "customer complain": "rag_customer_complain_retriever",
            # "promotion": "rag_promotion_retriever",
            # "give final response": "give_final_response",
            "final rag": "final_rag_retriever",
            "continue": "tool_execute",
            
        }
    )
    app = workflow.compile()
    return app

app = None 

def _prepare_chat_history(event_body):
    if "history_config" in event_body["chatbot_config"]:
        # experiment for chat history sep by goods_id
        goods_id = str(event_body['chatbot_config']['goods_id'])
        chat_history_by_goods_id = []
        for hist in event_body["chat_history"]:
            if goods_id == hist['additional_kwargs']['goods_id']:
                current_chat = {}
                current_chat['role'] = hist['role']
                current_chat['content'] = hist['content']
                current_chat['addional_kwargs'] = {}
                if 'goods_id' in hist['additional_kwargs']:
                    current_chat['addional_kwargs']['goods_id'] = str(hist['additional_kwargs']['goods_id'])
                chat_history_by_goods_id.append(current_chat)
        return chat_history_by_goods_id
    else:
        return event_body["chat_history"]

def retail_entry(event_body):
    """
    Entry point for the Lambda function.
    :param event_body: The event body for lambda function.
    return: answer(str)
    """
    global app,app_agent
    if app is None:
        app = build_graph(ChatbotState)
    
    if app_agent is None:
        app_agent = build_agent_graph(ChatbotState)

    # debuging
    # TODO only write when run local
    if is_running_local():
        with open('retail_entry_workflow.png','wb') as f:
            f.write(app.get_graph().draw_mermaid_png())
        
        with open('retail_entry_agent_workflow.png','wb') as f:
            f.write(app_agent.get_graph().draw_mermaid_png())
    ################################################################################
    # prepare inputs and invoke graph
    event_body['chatbot_config'] = parse_retail_entry_config(event_body['chatbot_config'])
    chatbot_config = event_body['chatbot_config']
    query = event_body['query']
    stream = event_body['stream']
    create_time = chatbot_config.get('create_time',None)
    message_id = event_body['custom_message_id']
    ws_connection_id = event_body['ws_connection_id']
    enable_trace = chatbot_config["enable_trace"]
    
    goods_info = ""
    human_goods_info = ""
    goods_id = str(event_body['chatbot_config']['goods_id'])
    if goods_id:
        try:
            _goods_info = json.loads(goods_dict.get(goods_id,{}).get("goods_info",""))
            _goods_type = goods_dict.get(goods_id,{}).get("goods_type","")
        except Exception as e:
            import traceback 
            error = traceback.format_exc()
            logger.error(f"error meesasge {error}, invalid goods_id: {goods_id}")
            _goods_info = None
        
        
        if _goods_info:
            logger.info(_goods_info)
            if _goods_type:
                goods_info = f"商品类型: \n<goods_type>\n{_goods_type}\n</goods_type>\n"
            else:
                goods_info = ""
            goods_info += f"<{goods_info_tag}>\n"
    
            human_goods_info = ""
            for k,v in _goods_info.items():
                goods_info += f"{k}:{v}\n" 
                human_goods_info += f"{k}:{v}\n" 
            
            goods_info = goods_info.strip()
            goods_info += f"\n</{goods_info_tag}>"

    use_history = chatbot_config['use_history']
    chat_history = _prepare_chat_history(event_body) if use_history else []
    event_body['chat_history'] = chat_history
    logger.info(f'event_body:\n{json.dumps(event_body,ensure_ascii=False,indent=2,cls=JSONEncoder)}')
    
    logger.info(f"goods_info: {goods_info}")
    logger.info(f"chat_hisotry: {chat_history}")
    # invoke graph and get results
    response = app.invoke({
        "stream": stream,
        "chatbot_config": chatbot_config,
        "query": query,
        "create_time": create_time,
        "enable_trace": enable_trace,
        "trace_infos": [],
        "message_id": message_id,
        "chat_history": chat_history,
        "agent_tool_history": [],
        "ws_connection_id": ws_connection_id,
        "debug_infos": {},
        "extra_response": {},
        "goods_info":goods_info,
        "human_goods_info":human_goods_info,
        "agent_llm_type": LLMTaskType.RETAIL_TOOL_CALLING,
        "query_rewrite_llm_type":LLMTaskType.RETAIL_CONVERSATION_SUMMARY_TYPE,
        "agent_repeated_call_limit": chatbot_config['agent_repeated_call_limit'],
        "agent_current_call_number": 0,
        "current_agent_intent_type":""
    })
    
    extra_response = response["extra_response"]
    return {
        "answer":response['answer'],
        **extra_response,
        "ddb_additional_kwargs": {
             "goods_id":goods_id,
             "current_agent_intent_type":extra_response.get('current_agent_intent_type',"")
        },
        "trace_infos":response['trace_infos'],
        }

main_chain_entry = retail_entry