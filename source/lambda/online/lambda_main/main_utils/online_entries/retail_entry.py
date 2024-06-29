import json
import re
import random
from textwrap import dedent
from typing import TypedDict,Any,Annotated
import validators
from langgraph.graph import StateGraph,END
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,node_monitor_wrapper
from common_logic.common_utils.python_utils import update_nest_dict,add_messages
from common_logic.common_utils.constant import (
    LLMTaskType
)

from functions.retail_tools.lambda_product_information_search.product_information_search import goods_dict
from functions.tool_execute_result_format import format_tool_call_results
from functions.tool_calling_parse import parse_tool_calling as _parse_tool_calling

from lambda_main.main_utils.parse_config import parse_retail_entry_config
from common_logic.common_utils.lambda_invoke_utils import send_trace,is_running_local
from common_logic.common_utils.exceptions import (
    ToolNotExistError,
    ToolParameterNotExistError,
    MultipleToolNameError,
    ToolNotFound
)
from common_logic.common_utils.logger_utils import get_logger
from common_logic.common_utils.serialization_utils import JSONEncoder


logger = get_logger('retail_entry')

class ChatbotState(TypedDict):
    chatbot_config: dict # chatbot config
    query: str 
    ws_connection_id: str 
    stream: bool 
    query_rewrite: str = None  # query rewrite ret
    intent_type: str = None # intent
    intention_fewshot_examples: list
    trace_infos: Annotated[list[str],add_messages]
    message_id: str = None
    chat_history: Annotated[list[dict],add_messages]
    agent_chat_history: Annotated[list[dict],add_messages]
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
    agent_recursion_limit: int # agent recursion limit
    current_agent_recursion_num: int
    enable_trace: bool

####################
# nodes in lambdas #
####################

@node_monitor_wrapper
def query_preprocess_lambda(state: ChatbotState):
    output:str = invoke_lambda(
        event_body=state,
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
def intention_detection_lambda(state: ChatbotState):
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
def agent_lambda(state: ChatbotState):
    goods_info = state.get('goods_info',None) or ""
    agent_chat_history = state.get('agent_chat_history',"")
    if agent_chat_history:
        search_result = agent_chat_history[-1]['additional_kwargs']['original'][0].get('search_result',1)
        if search_result == 0:
            context = agent_chat_history[-1]['additional_kwargs']['original'][0].get('result',"")
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
            current_agent_recursion_num = state['current_agent_recursion_num'] + 1
            current_agent_output = {}
            current_agent_output['agent_output'] = {}
            current_agent_output['agent_output']['function_calls'] = []
            current_agent_output['agent_output']['content'] = output
            current_agent_output['current_agent_model_id'] = "qwen2-72B-instruct"
            current_agent_output['current_agent_tools_def'] = []
            return {
                "current_agent_output": current_agent_output,
                "current_agent_recursion_num": current_agent_recursion_num
            }

    current_agent_output:dict = invoke_lambda(
        event_body={
            **state,
            "other_chain_kwargs":{"goods_info": goods_info}
        },
        lambda_name="Online_Agent",
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler"
    )
    current_agent_recursion_num = state['current_agent_recursion_num'] + 1
    send_trace(f"\n\n**current_agent_output:** \n{json.dumps(current_agent_output['agent_output'],ensure_ascii=False,indent=2)}\n\n **current_agent_recursion_num:** {current_agent_recursion_num}", state["stream"], state["ws_connection_id"])
    return {
        "current_agent_output": current_agent_output,
        "current_agent_recursion_num": current_agent_recursion_num
    }


@node_monitor_wrapper
def parse_tool_calling(state: ChatbotState):
    """executor lambda
    Args:
        state (NestUpdateState): _description_

    Returns:
        _type_: _description_
    """
    # parse tool_calls:
    try:
        output = _parse_tool_calling(
            agent_output=state['current_agent_output']
        )
        tool_calls = output['tool_calls']
        send_trace(f"\n\n**tool_calls parsed:** \n{tool_calls}", state["stream"], state["ws_connection_id"], state["enable_trace"])
        if not state["extra_response"].get("current_agent_intent_type", None):
            state["extra_response"]["current_agent_intent_type"] = output['tool_calls'][0]["name"]
       
        return {
            "parse_tool_calling_ok": True,
            "current_tool_calls": tool_calls,
            "agent_chat_history": [output['agent_message']]
        }
    
    except (ToolNotExistError,
             ToolParameterNotExistError,
             MultipleToolNameError,
             ToolNotFound
             ) as e:
        send_trace(f"\n\n**tool_calls parse failed:** \n{str(e)}", state["stream"], state["ws_connection_id"], state["enable_trace"])
        return {
            "parse_tool_calling_ok": False,
            "agent_chat_history":[
                e.agent_message,
                e.error_message
            ]
        }

@node_monitor_wrapper
def tool_execute_lambda(state: ChatbotState):
    """executor lambda
    Args:
        state (NestUpdateState): _description_

    Returns:
        _type_: _description_
    """
    tool_calls = state['current_tool_calls']
    assert len(tool_calls) == 1, tool_calls
    tool_call_results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_kwargs = tool_call['kwargs']
        # call tool
        output = invoke_lambda(
            event_body = {
                "tool_name":tool_name,
                "state":state,
                "kwargs":tool_kwargs
                },
            lambda_name="Online_Tool_Execute",
            lambda_module_path="functions.lambda_tool",
            handler_name="lambda_handler"   
        )
        tool_call_results.append({
            "name": tool_name,
            "output": output,
            "kwargs": tool_call['kwargs'],
            "model_id": tool_call['model_id']
        })
    
    output = format_tool_call_results(tool_call['model_id'],tool_call_results)
    send_trace(f'**tool_execute_res:** \n{output["tool_message"]["content"]}')
    return {
        "agent_chat_history": [output['tool_message']]
        }


@node_monitor_wrapper
def rag_daily_reception_retriever_lambda(state: ChatbotState):
    # call retriever
    retriever_params = state["chatbot_config"]["rag_daily_reception_config"]['retriever_config']
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]
    context = "\n\n".join(contexts)
    send_trace(f'**rag_goods_exchange_retriever** {context}', state["stream"], state["ws_connection_id"])
    return {"contexts": contexts}

@node_monitor_wrapper
def rag_daily_reception_llm_lambda(state:ChatbotState):
    context = "\n\n".join(state['contexts'])
    system_prompt = (f"你是安踏的客服助理，正在帮用户解答问题，客户提出的问题大多是属于日常接待类别，你需要按照下面的guidelines进行回复:\n"
                    "<guidelines>\n"
                    " - 回复内容需要展现出礼貌。回答内容为一句话，言简意赅。\n"
                    " - 使用中文回答。\n"
                    "</guidelines>\n"
                    "下面列举了一些具体的场景下的回复，你可以结合用户的问题进行参考:\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>"
                )
    
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_daily_reception_config']['llm_config'], 
                "system_prompt": system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": {"query": state['query'], "chat_history": state['chat_history']}
            }
        )
    return {"answer": output}

@node_monitor_wrapper
def rag_goods_exchange_retriever_lambda(state: ChatbotState):
    # call retriever
    retriever_params = state["chatbot_config"]["rag_goods_exchange_config"]['retriever_config']
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n\n".join(contexts)
    send_trace(f'**rag_goods_exchange_retriever** {context}', state["stream"], state["ws_connection_id"])
    return {"contexts": contexts}


@node_monitor_wrapper
def rag_goods_exchange_llm_lambda(state:ChatbotState):
    context = "\n\n".join(state['contexts'])
    system_prompt = (f"你是安踏的客服助理，正在帮用户解答问题，客户提出的问题大多是属于商品退换货范畴，你需要按照下面的guidelines进行回复:\n"
                    "<guidelines>\n"
                    " - 回复内容需要展现出礼貌。回答内容为一句话，言简意赅。\n"
                    " - 使用中文回答。\n"
                    "</guidelines>\n"
                    "下面列举了一些具体的场景下的回复，你可以结合用户的问题进行参考回答:\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>\n"
                )
    
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_goods_exchange_config']['llm_config'],
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
            }
        )
    return {"answer": output}

@node_monitor_wrapper
def rag_product_aftersales_retriever_lambda(state: ChatbotState):
    # call retriever
    recent_tool_calling:list[dict] = state['current_tool_calls'][0]
    if "shop" in recent_tool_calling['kwargs'] and recent_tool_calling['kwargs']['shop'] != "tianmao":
        contexts = ["顾客不是在天猫购买的商品，请他咨询其他商家"]
        return {"contexts": contexts}
    retriever_params = state["chatbot_config"]["rag_product_aftersales_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n\n".join(contexts)
    send_trace(f'**rag_product_aftersales_retriever** {context}', state["stream"], state["ws_connection_id"])
    return {"contexts": contexts}

@node_monitor_wrapper
def rag_product_aftersales_llm_lambda(state:ChatbotState):
    context = "\n\n".join(state['contexts'])
    system_prompt = (f"你是安踏的客服助理，正在帮消费者解答问题，消费者提出的问题大多是属于商品的质量和物流规则。context列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>\n"
                    "你需要按照下面的guidelines对消费者的问题进行回答:\n"
                    "<guidelines>\n"
                    " - 回答内容为一句话，言简意赅。\n"
                    " - 如果问题与context内容不相关，就不要采用。\n"
                    " - 消费者的问题里面可能包含口语化的表达，比如鞋子开胶的意思是用胶黏合的鞋体裂开。这和胶丝遗留没有关系\n"
                    "</guidelines>\n"
                    )
    # print('llm config',state['chatbot_config']['rag_product_aftersales_config']['llm_config'])
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_product_aftersales_config']['llm_config'], 
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT
            },
            "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
            }
        )
    return {"answer": output}

@node_monitor_wrapper
def rag_customer_complain_retriever_lambda(state: ChatbotState):
    # call retriever
    retriever_params = state["chatbot_config"]["rag_customer_complain_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n\n".join(contexts)
    send_trace(f'**rag_customer_complain_retriever** {context}', state["stream"], state["ws_connection_id"])
    return {"contexts": contexts}

@node_monitor_wrapper
def rag_customer_complain_llm_lambda(state:ChatbotState):
    context = "\n\n".join(state['contexts'])
    # prompt = dedent(f"""你是安踏的客服助理，正在处理有关于客户抱怨的问题，这些问题有关于商品质量等方面，需要你按照下面的guidelines进行回复:
    system_prompt = ("你是安踏的客服助理，正在处理有关于消费者抱怨的问题。context列举了一些可能和客户问题有关的具体场景及回复，你可以进行参考:\n"
                    "<context>\n"
                    f"{context}\n"
                    "</context>\n"
                    "需要你按照下面的guidelines进行回复:\n"
                    "<guidelines>\n"
                    " - 回答内容为一句话，言简意赅。\n"
                    " - 尽量安抚客户情绪。\n"
                    " - 直接回答，不要说\"亲爱的顾客，您好\"\n"
                    "</guidelines>\n"
                    )
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_customer_complain_config']['llm_config'],
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
            }
        )
    return {"answer": output}

@node_monitor_wrapper
def rag_promotion_retriever_lambda(state: ChatbotState):
    # call retriever
    retriever_params = state["chatbot_config"]["rag_promotion_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output:str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler"
    )
    contexts = [doc['page_content'] for doc in output['result']['docs']]

    context = "\n\n".join(contexts)
    send_trace(f'**rag_promotion_retriever** {context}', state["stream"], state["ws_connection_id"])
    return {"contexts": contexts}

@node_monitor_wrapper
def rag_promotion_llm_lambda(state:ChatbotState):
    context = "\n\n".join(state['contexts'])

    system_prompt = ("你是安踏的客服助理，正在帮消费者解答有关于商品促销的问题，这些问题是有关于积分、奖品、奖励等方面。\n"
                     "context列举了一些可能有关的具体场景及回复，你可以进行参考:\n"
                    f"<context>\n{context}\n</context>\n"
                    "你需要按照下面的guidelines对消费者的问题进行回答:\n"
                    "<guidelines>\n"
                    " - 回答内容为一句话，言简意赅。\n"
                    " - 如果问题与context内容不相关，就不要采用。\n"
                    " - 使用中文进行回答。\n"
                    "</guidelines>"
    )
   
    output:str = invoke_lambda(
        lambda_name='Online_LLM_Generate',
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name='lambda_handler',
        event_body={
            "llm_config": {
                **state['chatbot_config']['rag_promotion_config']['llm_config'],
                "system_prompt":system_prompt,
                "intent_type": LLMTaskType.CHAT},
            "llm_input": { "query": state['query'], "chat_history": state['chat_history']}
            }
        )
    return {"answer": output}



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


def transfer_reply(state:ChatbotState):
    return {"answer": "立即为您转人工客服，请稍后"}


def give_rhetorical_question(state:ChatbotState):
    recent_tool_calling:list[dict] = state['current_tool_calls'][0]
    return {"answer": recent_tool_calling['kwargs']['question']}


def give_final_response(state:ChatbotState):
    recent_tool_calling:list[dict] = state['current_tool_calls'][0]
    return {"answer": recent_tool_calling['kwargs']['response']}

def rule_url_reply(state:ChatbotState):
    state["extra_response"]["current_agent_intent_type"] = "rule reply"
    if state['query'].endswith(('.jpg','.png')):
        answer = random.choice([
            "收到，亲。请问我们可以怎么为您效劳呢？。",
            "您好，请问有什么需要帮助的吗？"
        ])
        return {"answer": answer}
    # product information
    r = re.findall(r"item.htm\?id=(.*)",state['query'])
    if r:
        goods_id = r[0]
    else:
        goods_id = 0
    if goods_id in goods_dict:
        # call llm to make summary of goods info
        human_goods_info = state['human_goods_info']
        output = f"您好，该商品的特点是:\n{human_goods_info}"
        if human_goods_info:
            system_prompt = (f"你是安踏的客服助理，当前用户对下面的商品感兴趣:\n"
                        f"<goods_info>\n{human_goods_info}\n</goods_info>\n"
                        "请你结合商品的基础信息，特别是卖点信息返回一句推荐语。"
                    )
            output:str = invoke_lambda(
                lambda_name='Online_LLM_Generate',
                lambda_module_path="lambda_llm_generate.llm_generate",
                handler_name='lambda_handler',
                event_body={
                    "llm_config": {
                        **state['chatbot_config']['rag_daily_reception_config']['llm_config'], 
                        "system_prompt": system_prompt,
                        "intent_type": LLMTaskType.CHAT},
                    "llm_input": {"query": state['query'], "chat_history": state['chat_history']}
                        }
                    )
         
        return {"answer":output}
    
    return {"answer":"您好"}

def rule_number_reply(state:ChatbotState):
    state["extra_response"]["current_agent_intent_type"] = "rule reply"
    return {"answer":"收到订单信息"}


################
# define edges #
################

def query_route(state:dict):
    # check if rule reply
    query = state['query']
    if validators.url(query):
        return "url"
    if query.isnumeric() and len(query)>=8:
        return "number"
    else:
        return "continue"

def intent_route(state:dict):
    return state['intent_type']

def agent_route(state:dict):
    parse_tool_calling_ok = state['parse_tool_calling_ok']
    if not parse_tool_calling_ok:
        if state['current_agent_recursion_num'] >= state['agent_recursion_limit']:
            send_trace(f"Reach the agent recursion limit: {state['agent_recursion_limit']}, route to final rag")
            return 'final rag'
        return 'invalid tool calling'
    
    recent_tool_calls:list[dict] = state['current_tool_calls']
    
    recent_tool_call = recent_tool_calls[0]

    recent_tool_name = recent_tool_call['name']

    if recent_tool_name in ['comfort', 'transfer']:
        return recent_tool_name
    
    if recent_tool_call['name'] == "give_rhetorical_question":
        return "rhetorical question"
    
    if recent_tool_call['name'] == "goods_exchange":
        return "goods exchange"
    
    if recent_tool_call['name'] == "daily_reception":
        return "daily reception"

    if recent_tool_call['name'] == "rule_response":
        return "rule response"

    if recent_tool_call['name'] == 'product_logistics':
        return "product aftersales"

    if recent_tool_call['name'] == 'product_quality':
        return "product aftersales"

    if recent_tool_call['name'] == 'customer_complain':
        return "customer complain"

    if recent_tool_call['name'] == 'promotion':
        return "promotion"
    
    if recent_tool_call['name'] == "give_final_response":
        return "give final response"

    if state['current_agent_recursion_num'] >= state['agent_recursion_limit']:
        send_trace(f"Reach the agent recursion limit: {state['agent_recursion_limit']}, route to final rag")
        return 'final rag'

    return "continue"


     
#############################
# define whole online graph #
#############################

def build_graph():
    workflow = StateGraph(ChatbotState)
    # add all nodes
    workflow.add_node("query_preprocess_lambda", query_preprocess_lambda)
    workflow.add_node("intention_detection_lambda", intention_detection_lambda)
    workflow.add_node("agent_lambda", agent_lambda)
    workflow.add_node("tool_execute_lambda", tool_execute_lambda)
    workflow.add_node("transfer_reply", transfer_reply)
    workflow.add_node("give_rhetorical_question",give_rhetorical_question)
    workflow.add_node("give_final_response",give_final_response)
    # workflow.add_node("give_response_wo_tool",give_response_without_any_tool)
    workflow.add_node("parse_tool_calling",parse_tool_calling)
    # 
    workflow.add_node("rag_daily_reception_retriever",rag_daily_reception_retriever_lambda)
    workflow.add_node("rag_daily_reception_llm",rag_daily_reception_llm_lambda)
    workflow.add_node("rag_goods_exchange_retriever",rag_goods_exchange_retriever_lambda)
    workflow.add_node("rag_goods_exchange_llm",rag_goods_exchange_llm_lambda)
    workflow.add_node("rag_product_aftersales_retriever",rag_product_aftersales_retriever_lambda)
    workflow.add_node("rag_product_aftersales_llm",rag_product_aftersales_llm_lambda)
    workflow.add_node("rag_customer_complain_retriever",rag_customer_complain_retriever_lambda)
    workflow.add_node("rag_customer_complain_llm",rag_customer_complain_llm_lambda)
    workflow.add_node("rule_url_reply",rule_url_reply)
    workflow.add_node("rule_number_reply",rule_number_reply)
    workflow.add_node("rag_promotion_retriever",rag_promotion_retriever_lambda)
    workflow.add_node("rag_promotion_llm",rag_promotion_llm_lambda)
    workflow.add_node("final_rag_retriever",final_rag_retriever_lambda)
    workflow.add_node("final_rag_llm",final_rag_llm_lambda)

    # add all edges
    workflow.set_entry_point("query_preprocess_lambda")
    # workflow.add_edge("query_preprocess_lambda","intention_detection_lambda")
    workflow.add_edge("intention_detection_lambda","agent_lambda")
    workflow.add_edge("tool_execute_lambda","agent_lambda")
    workflow.add_edge("agent_lambda",'parse_tool_calling')
    workflow.add_edge("rag_daily_reception_retriever","rag_daily_reception_llm")
    workflow.add_edge('rag_goods_exchange_retriever',"rag_goods_exchange_llm")
    workflow.add_edge('rag_product_aftersales_retriever',"rag_product_aftersales_llm")
    workflow.add_edge('rag_customer_complain_retriever',"rag_customer_complain_llm")
    workflow.add_edge('rag_promotion_retriever',"rag_promotion_llm")
    workflow.add_edge('final_rag_retriever',"final_rag_llm")
    
    # end
    workflow.add_edge("transfer_reply",END)
    workflow.add_edge("give_rhetorical_question",END)
    # workflow.add_edge("give_response_wo_tool",END)
    workflow.add_edge("rag_daily_reception_llm",END)
    workflow.add_edge("rag_goods_exchange_llm",END)
    workflow.add_edge("rag_product_aftersales_llm",END)
    workflow.add_edge("rag_customer_complain_llm",END)
    workflow.add_edge('rule_url_reply',END)
    workflow.add_edge('rule_number_reply',END)
    workflow.add_edge("rag_promotion_llm",END)
    workflow.add_edge("give_final_response",END)
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
            "rhetorical question": "give_rhetorical_question",
            "transfer": "transfer_reply",
            "goods exchange": "rag_goods_exchange_retriever",
            "daily reception": "rag_daily_reception_retriever",
            "product aftersales": "rag_product_aftersales_retriever",
            "customer complain": "rag_customer_complain_retriever",
            "promotion": "rag_promotion_retriever",
            "give final response": "give_final_response",
            "final rag": "final_rag_retriever",
            "continue": "tool_execute_lambda",
            
        }
    )
    app = workflow.compile()
    return app

app = None 

def retail_entry(event_body):
    """
    Entry point for the Lambda function.
    :param event_body: The event body for lambda function.
    return: answer(str)
    """
    global app 
    if app is None:
        app = build_graph()

    # debuging
    # TODO only write when run local
    if is_running_local():
        with open('retail_entry_workflow.png','wb') as f:
            f.write(app.get_graph().draw_png())
    
    ################################################################################
    # prepare inputs and invoke graph
    event_body['chatbot_config'] = parse_retail_entry_config(event_body['chatbot_config'])
    logger.info(f'event_body:\n{json.dumps(event_body,ensure_ascii=False,indent=2,cls=JSONEncoder)}')
    chatbot_config = event_body['chatbot_config']
    query = event_body['query']
    use_history = chatbot_config['use_history']
    chat_history = event_body['chat_history'] if use_history else []
    stream = event_body['stream']
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
            goods_info += "<goods_info>\n"
            human_goods_info = ""
            for k,v in _goods_info.items():
                goods_info += f"{k}:{v}\n" 
                human_goods_info += f"{k}:{v}\n" 
            goods_info += "\n</goods_info>"
    
    logger.info(f"goods_info: {goods_info}")
    # invoke graph and get results
    response = app.invoke({
        "stream": stream,
        "chatbot_config": chatbot_config,
        "query": query,
        "enable_trace": enable_trace,
        "trace_infos": [],
        "message_id": message_id,
        "chat_history": chat_history,
        "agent_chat_history": [],
        "ws_connection_id": ws_connection_id,
        "debug_infos": {},
        "extra_response": {},
        "goods_info":goods_info,
        "human_goods_info":human_goods_info,
        "agent_llm_type": LLMTaskType.RETAIL_TOOL_CALLING,
        "query_rewrite_llm_type":LLMTaskType.RETAIL_CONVERSATION_SUMMARY_TYPE,
        "agent_recursion_limit": chatbot_config['agent_recursion_limit'],
        "current_agent_recursion_num": 0,
    })

    return {"answer":response['answer'],**response["extra_response"],"trace_infos":response['trace_infos']}

main_chain_entry = retail_entry