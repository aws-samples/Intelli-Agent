import json 
import os
from typing import TypedDict,Any
from langgraph.graph import StateGraph,END

# from .. import parse_config

# fast reply
INVALID_QUERY = "请重新描述您的问题。请注意：\n不能过于简短也不能超过500个字符\n不能包含个人信息（身份证号、手机号等）"
INVALID_INTENTION = "很抱歉，我只能回答与知识问答相关的咨询。"
KNOWLEDGE_QA_INSUFFICIENT_CONTEXT = "很抱歉，根据我目前掌握到的信息无法给出回答。"

class AppState(TypedDict):
    keys: Any
################
# local nodes #
################
def fast_reply(
        state
    ):
    
    state = state['keys']
    answer = state['answer']

    output = {
            "answer": answer,
            # "sources": [],
            "contexts": [],
            "context_docs": []
    }
    state.update(output)

################
# local branches #
################
def is_query_valid(state):
    state = state['keys']
    if state['is_query_invalid']:
        state['answer'] = INVALID_QUERY
        return 'invalid query'
    return "valid query"

def is_intention_valid(state):
    state = state['keys']
    if state['is_intention_invalid']:
        state['answer'] = INVALID_INTENTION
        return 'invalid intention'
    return "valid intention"

def is_context_enough(state):
    state = state['keys']
    return "enough"

################
# nodes in lambdas #
################

def query_preprocess_lambda(state: AppState):
    state = state['keys']
    # run in lambda
    state['is_query_invalid'] = True

def intention_detection_lambda(state: AppState):
    state = state['keys']
    # run in lambda
    state['is_intention_invalid'] = True

def agent_lambda(state: AppState):
    state['is_intention_invalid'] = True
    # run in lambda
    state = state['keys']

def function_call_lambda(state: AppState):
    state = state['keys']
    # run in lambda

def llm_generate_lambda(state: AppState):
    state = state['keys']
    # run in lambda
    
################
# define whole online graph #
################
workflow = StateGraph(AppState)
# add all nodes
workflow.add_node("query_preprocess_lambda", query_preprocess_lambda)
workflow.add_node("intention_detection_lambda", intention_detection_lambda)
workflow.add_node("agent_lambda", agent_lambda)
workflow.add_node("function_call_lambda", function_call_lambda)
workflow.add_node("llm_generate_lambda", llm_generate_lambda)
workflow.add_node("fast_reply", fast_reply)
# block 1: query preprocess
# contents:
# 1. check whether query contains invalid information, like PII 
# 2. query rewrite, rewrite query based on chat history
workflow.set_entry_point("query_preprocess_lambda")
# decide whether it is a valid query
workflow.add_conditional_edges(
    "query_preprocess_lambda",
    is_query_valid,
    {
        "invalid query": "fast_reply",
        "valid query": "intention_detection_lambda"
    }
)
# block 2: intention detection
# contents:
# 1. detect user intention according to sample queries injected
# decide whether it is a valid intention
# block 3: query enhancement and function choose
# contents:
# 1. according to detected intention, choose the functions to call, like retriever
# web search, api call
# 2. format input query according to chosen functions
# 2.1 query expansion for retriever
# 2.2 add call parameters for api call
workflow.add_conditional_edges(
    "intention_detection_lambda",
    is_intention_valid,
    {
        "invalid intention": "fast_reply",
        "valid intention": "agent_lambda"
    }
)
# block 4: run functions to get enough context for llm
# contents:
# 1. run different functions in function_call, like retriever, web search or call
# api
# 2. when enough context is collected or the max try is reached, go to next stage.
# otherwise, the query_enhance_and_function_choose should be re-run
workflow.add_edge("function_call_lambda","agent_lambda")
workflow.add_conditional_edges(
    "agent_lambda",
    is_context_enough,
    {
        "insufficient context": "function_call_lambda",
        "enough context": "llm_generate_lambda",
        "invalid context": "fast_reply",
    }
)
# end blocks when the whole logic is finished
# contents:
# 1. fast reply
# 2. rag llm generate 
workflow.add_edge("fast_reply", END)
workflow.add_edge("llm_generate_lambda", END)
app = workflow.compile()

simple_workflow = StateGraph(AppState)
# add all nodes
simple_workflow.add_node("query_preprocess_lambda", query_preprocess_lambda)
simple_workflow.set_entry_point("query_preprocess_lambda")
# decide whether it is a valid query
simple_workflow.add_conditional_edges(
    "query_preprocess_lambda",
    is_query_valid,
    {
        "invalid query": END,
        "valid query": END
    }
)
app = simple_workflow.compile()

# # uncomment the following lines to save the graph
with open('common_entry_workflow.png','wb') as f:
    f.write(app.get_graph().draw_png())
# app.get_graph().print_ascii()

def common_entry(
    event_body
):
    """
    Entry point for the Lambda function.

    :param event_body: The event body for lambda function.
    return: answer(str)
    """


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
            "chat_history": rag_config['chat_history'][-6:] if rag_config['use_history'] else [],
            "rag_config": rag_config,
            "message_id": message_id,
            "stream": stream,
            # "qq_workspace_list": qq_workspace_list,
            # "qd_workspace_list": qd_workspace_list,
            "trace_infos":trace_infos,
            "intent_embedding_endpoint_name": os.environ['intent_recognition_embedding_endpoint'],
            # "query_lang": "zh"
    }
    # invoke graph and get results
    response = app.invoke({"keys":inputs})['keys']
    # trace_info = format_trace_infos(trace_infos)
    # logger.info(f'session_id: {rag_config["session_id"]}, chain trace info:\n{trace_info}')
    
    response['rag_config'] = rag_config
    return response

main_chain_entry = common_entry