import sys
import operator

# sys.path.append("/efs/projects/aws-samples-llm-bot-branches/aws-samples-llm-bot-dev-online-refactor/source/lambda/online/layer_logic")
import json 
import os
from typing import TypedDict,Any,Annotated
from langgraph.graph import StateGraph,END
from common_utils.lambda_invoke_utils import invoke_lambda,chatbot_lambda_call_wrapper
from common_utils.langchain_utils import update_nest_dict
from functions.tools import get_tool_by_name,Tool
from functions.tool_execute_result_format import format_tool_execute_result
# from .. import parse_config
# fast reply
# INVALID_QUERY = "请重新描述您的问题。请注意：\n不能过于简短也不能超过500个字符\n不能包含个人信息（身份证号、手机号等）"
# INVALID_INTENTION = "很抱歉，我只能回答与知识问答相关的咨询。"
# KNOWLEDGE_QA_INVALID_CONTEXT = "很抱歉，根据我目前掌握到的信息无法给出回答。"

# class AppState(TypedDict):
#     keys: Annotated
################
# local nodes #
################
# def fast_reply(
#         answer:str
#     ):

#     output = {
#             "answer": answer,
#             "sources": [],
#             "contexts": [],
#             "context_docs": []
#     }
#     return output

################
# local branches #
################


# def intent_route(state):
#     state = state['keys']
#     intent = state['intention']

#     return intent
    
    # if intent == "comfort":
    #     return "comfort"
    # elif intent "transfer":

    # if state['is_query_valid'] == True:
    #     return "valid query"
    # else:
    #     state['answer'] = INVALID_QUERY
    #     return 'invalid query'

# def is_intention_valid(state):
#     state = state['keys']
#     if state['is_intention_valid']:
#         return "valid intention"
#     else:
#         state['answer'] = INVALID_INTENTION
#         return 'invalid intention'

# def is_context_enough(state):
#     state = state['keys']
#     if state['is_context_enough'] == 'invalid context':
#         state['answer'] = KNOWLEDGE_QA_INVALID_CONTEXT
#     return state['is_context_enough']


class ChatbotState(TypedDict):
    chatbot_config: dict # 配置项
    query: str # 用户的问题
    query_rewrite: str = None  # query rewrite ret
    intent_type: str = None # intent
    trace_infos: list = Annotated[list[str],operator.add]
    message_id: str = None
    chat_history: list[dict] = Annotated[list[dict],operator.add]
    current_tool_calls: dict
    current_tool_execute_res: dict
    debug_infos: dict = Annotated[dict,update_nest_dict]
    answer: Any  # 最后的结果
    current_monitor_msg: dict # 当前的监控信息
    

####################
# nodes in lambdas #
####################

def query_preprocess_lambda(state: ChatbotState):
    output:str = invoke_lambda(
        event_body=state,
        lambda_name="Online_Query_Preprocess",
        lambda_module_path="lambda_query_preprocess.query_preprocess",
        handler_name="lambda_handler"
    )
    return {"query_rewrite":output}

def intention_detection_lambda(state: ChatbotState):
    output:str = invoke_lambda(
        event_body=state,
        lambda_name="Online_Intention_Detection",
        lambda_module_path="lambda_intention_detection.intention",
        handler_name="lambda_handler"
    )
    return {"intent_type":output}

def agent_lambda(state: ChatbotState):
    output:dict = invoke_lambda(
        event_body=state,
        lambda_name="Online_Agent",
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler"
    )
    
    # tool_calling_res = state.get('tool_calling_res',[])

    # tool_calling_res.append(output)
   
    return {
        "current_tool_calls": output['current_tool_calls'],
        "chat_history": [{
                    "role": "ai",
                    "content": output['content']
                }]
        }
    

def tool_execute_lambda(state: ChatbotState):
    """executor lambda
    Args:
        state (NestUpdateState): _description_

    Returns:
        _type_: _description_
    """
    tool_calls = state['current_tool_calls']
    # assert len(tool_calls) == 1, tool_calls
    
    tool_call_results = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        event_body = tool_call['args']
        tool:Tool = get_tool_by_name(tool_name)
        # call tool
        output:dict = invoke_lambda(
            event_body=event_body,
            lambda_name=tool.lambda_name,
            lambda_module_path=tool.lambda_module_path,
            handler_name=tool.handler_name
        )

        tool_call_results.append({
            "name": tool_name,
            "output": output,
            "kwargs": tool_call['args'],
            "model_id": tool_call['model_id']
        })
    
    # convert tool calling as chat history
    tool_call_result_strs = []
    for tool_call_result in tool_call_results:
        tool_exe_output = tool_call_result['output']
        ret:str = format_tool_execute_result(
            tool_call_result["model_id"],
            tool_exe_output
        )
        tool_call_result_strs.append(ret)

    return {"chat_history":[{
        "role":"user",
        "content": "\n".join(tool_call_result_strs)
    }]}
    

# def tag_llm_generate_lambda(state: NestUpdateState):
#     """
#     基于各类工具的结果进行生成
#     Args:
#         state (NestUpdateState): _description_
#     Returns:
#         _type_: _description_
#     """
#     # state = state['keys']
#     # # run in lambda
#     # msg = {"query": state['query']}
#     # invoke_response = lambda_client.invoke(FunctionName="Online_LLM_Generate",
#     #                                     InvocationType='RequestResponse',
#     #                                     Payload=json.dumps(msg))
#     # response_body = invoke_response['Payload']

#     # response_str = response_body.read().decode("unicode_escape")
#     # response_str = response_str.strip('"')

#     # response = json.loads(response_str)
#     # state['answer'] = response['body']['answer']
#     state = state['keys']
#     output:dict = invoke_lambda(
#         event_body={
#             "llm_config":'xx',
#             "llm_inputs": state
#         },
#         lambda_name="Online_LLM_Generate",
#         lambda_module_path="lambda_llm_generate.llm_generate",
#         handler_name="lambda_handler"
#     )
#     return {"keys":output}


def chat_llm_generate_lambda(state:ChatbotState):
    answer:dict = invoke_lambda(
        event_body={
            "llm_config":'xx',
            "llm_inputs": state
        },
        lambda_name="Online_LLM_Generate",
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name="lambda_handler"
    )

    return {"answer":answer}


def comfort_reply(state:ChatbotState):
    return {"answer": "不好意思没能帮到您，是否帮你转人工客服？"}


def transfer_reply(state:ChatbotState):
    return {"answer": "立即为您转人工客服，请稍后"}


def give_rhetorical_question(state:ChatbotState):
    current_tool_calls:list[dict] = state['current_tool_calls']
    recent_tool_calling = current_tool_calls['tool_calls'][0]
    return {"answer": recent_tool_calling['args']['question']}


def give_tool_response(state:ChatbotState):
    tool_calling_res:list[dict] = state['current_tool_calls']
    recent_tool_calling = tool_calling_res['tool_calls'][0]
    return {"answer": recent_tool_calling['args']['response']}


def give_response_without_any_tool(state:ChatbotState):
    chat_history = state['chat_history']
    return {"answer": chat_history[-1]['content']}

################
# define edges #
################

def intent_route(state:dict):
    return state['intent_type']

def agent_route(state:dict):
    current_tool_calls:list[dict] = state['current_tool_calls']
    recent_tool_calls = current_tool_calls['tool_calls']
    if not recent_tool_calls:
        return "不使用工具"
    
    recent_tool_call = recent_tool_calls[0]
    # 反问
    if recent_tool_call['name'] == "give_rhetorical_question":
        return "反问"

    if recent_tool_call['name'] == "give_final_response":
        return "回答"

    return "继续"
     

################
# define whole online graph #
################

def build_graph():
    workflow = StateGraph(ChatbotState)
    # add all nodes
    workflow.add_node("query_preprocess_lambda", query_preprocess_lambda)
    workflow.add_node("intention_detection_lambda", intention_detection_lambda)
    workflow.add_node("agent_lambda", agent_lambda)
    workflow.add_node("tool_execute_lambda", tool_execute_lambda)
    # workflow.add_node("rag_llm_generate_lambda", tag_llm_generate_lambda)
    workflow.add_node("chat_llm_generate_lambda", chat_llm_generate_lambda)
    workflow.add_node("comfort_reply",comfort_reply)
    workflow.add_node("transfer_reply", transfer_reply)
    workflow.add_node("give_rhetorical_question",give_rhetorical_question)
    workflow.add_node("give_tool_response",give_tool_response)
    workflow.add_node("give_response_wo_tool",give_response_without_any_tool)

    # block 1: query preprocess
    # contents:
    # 1. check whether query contains invalid information, like PII 
    # 2. query rewrite, rewrite query based on chat history
    workflow.set_entry_point("query_preprocess_lambda")
    workflow.add_edge("query_preprocess_lambda","intention_detection_lambda")
    workflow.add_edge("tool_execute_lambda","agent_lambda")
    workflow.add_edge("comfort_reply",END)
    workflow.add_edge("transfer_reply",END)
    workflow.add_edge("chat_llm_generate_lambda",END)
    workflow.add_edge("give_rhetorical_question",END)
    workflow.add_edge("give_tool_response",END)
    workflow.add_edge("give_response_wo_tool",END)

    # decide whether it is a valid query
    workflow.add_conditional_edges(
        "intention_detection_lambda",
        intent_route,
        {
            "comfort": "comfort_reply",
            "transfer": "transfer_reply",
            "chat": "chat_llm_generate_lambda",
            "other": "agent_lambda"
        }
    )

    workflow.add_conditional_edges(
        "agent_lambda",
        agent_route,
        {
            "不使用工具": "give_response_wo_tool",
            "反问": "give_rhetorical_question",
            "回答": "give_final_response",
            "继续":"tool_execute_lambda"
        }
    )
    app = workflow.compile()
    return app


app = None 
def common_entry(
    event_body
):
    """
    Entry point for the Lambda function.
    :param event_body: The event body for lambda function.
    return: answer(str)
    """
    global app 
    app = build_graph()
    with open('common_entry_workflow.png','wb') as f:
        f.write(app.get_graph().draw_mermaid_png())

    ################################################################################
    # prepare inputs and invoke graph
    # rag_config = parse_config.parse_common_entry_config(event_body)
    rag_config = event_body
    # logger.info(f'common entry configs:\n {json.dumps(rag_config,indent=2,ensure_ascii=False,cls=JSONEncoder)}')
    query_input = event_body['question']
    stream = event_body['stream']
    message_id = event_body['custom_message_id']
    # workspace ids for retriever
    # qq_workspace_list, qd_workspace_list = prepare_workspace_lists(rag_config)
    # record debug info and trace info
    debug_info = {
        "response_msg": "normal"
    }
    trace_infos = []
    # construct whole inputs
    inputs = {
            "query": query_input,
            "debug_info": debug_info,
            # "intent_type": intent_type,
            # "intent_info": intent_info,
            # "chat_history": rag_config['chat_history'][-6:] if rag_config['use_history'] else [],
            "rag_config": rag_config,
            "message_id": message_id,
            "stream": stream,
            # "qq_workspace_list": qq_workspace_list,
            # "qd_workspace_list": qd_workspace_list,
            "trace_infos":trace_infos,
            # "intent_embedding_endpoint_name": os.environ['intent_recognition_embedding_endpoint'],
            # "query_lang": "zh"
    }
    # invoke graph and get results
    response = app.invoke({"keys":inputs})['keys']
    # trace_info = format_trace_infos(trace_infos)
    # logger.info(f'session_id: {rag_config["session_id"]}, chain trace info:\n{trace_info}')

    response['rag_config'] = rag_config
    return response

main_chain_entry = common_entry