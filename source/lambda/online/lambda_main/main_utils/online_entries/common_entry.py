from typing import TypedDict,Any,Annotated
from langgraph.graph import StateGraph,END
from common_utils.lambda_invoke_utils import invoke_lambda,node_monitor_wrapper
from common_utils.python_utils import update_nest_dict,add_messages

from functions.tools import get_tool_by_name,Tool
from functions.tool_execute_result_format import format_tool_execute_result
from lambda_main.main_utils.parse_config import parse_common_entry_config
from common_utils.lambda_invoke_utils import send_trace


class ChatbotState(TypedDict):
    chatbot_config: dict # chatbot config
    query: str 
    ws_connection_id: str 
    stream: bool 
    query_rewrite: str = None  # query rewrite ret
    intent_type: str = None # intent
    trace_infos: Annotated[list[str],add_messages]
    message_id: str = None
    chat_history: Annotated[list[dict],add_messages]
    agent_chat_history: Annotated[list[dict],add_messages]
    current_tool_calls: dict
    current_tool_execute_res: dict
    debug_infos: Annotated[dict,update_nest_dict]
    answer: Any  # final answer
    current_monitor_infos: str 
    extra_response: Annotated[dict,update_nest_dict]
    default_mode: bool = True   # yuanbo mode
    

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
    return {
        "query_rewrite":output,
        "current_monitor_infos":f"query_rewrite: {output}"
        }

@node_monitor_wrapper
def intention_detection_lambda(state: ChatbotState):
    # output:str = invoke_lambda(
    #     event_body=state,
    #     lambda_name="Online_Intention_Detection",
    #     lambda_module_path="lambda_intention_detection.intention",
    #     handler_name="lambda_handler"
    # )
    output = "other"
    if state.get("use_qa"):
        output = "qa"
    return {
        "intent_type":output,
        "current_monitor_infos":f"intent_type: {output}"
        }


@node_monitor_wrapper
def rag_retrieve_lambda(state: ChatbotState):
    # call retrivever 
    return None 


@node_monitor_wrapper
def rag_llm_lambda(state:ChatbotState):
    return None 


@node_monitor_wrapper
def agent_lambda(state: ChatbotState):
    output:dict = invoke_lambda(
        event_body={**state,"chat_history":state['agent_chat_history']},
        lambda_name="Online_Agent",
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler"
    )
    
    current_tool_calls = output['tool_calls']
    return {
        "current_monitor_infos":f"current_tool_calls: {current_tool_calls}",
        "current_tool_calls": current_tool_calls,
        "agent_chat_history": [{
                    "role": "ai",
                    "content": output['content']
                }]
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
        tool_exe_output['tool_name'] = tool_call_result['name']
        ret:str = format_tool_execute_result(
            tool_call_result["model_id"],
            tool_exe_output
        )
        tool_call_result_strs.append(ret)
    
    ret = "\n".join(tool_call_result_strs)
    return {
        "current_monitor_infos": ret,
        "agent_chat_history":[{
            "role": "user",
            "content": ret
    }]}
    


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
    recent_tool_calling:list[dict] = state['current_tool_calls'][0]
    return {"answer": recent_tool_calling['args']['question']}


def give_tool_response(state:ChatbotState):
    recent_tool_calling:list[dict] = state['current_tool_calls'][0]
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
    recent_tool_calls:list[dict] = state['current_tool_calls']
    if not recent_tool_calls:
        return "no tool"
    
    recent_tool_call = recent_tool_calls[0]
    # 反问
    if recent_tool_call['name'] == "give_rhetorical_question":
        return "rhetorical question"

    if recent_tool_call['name'] == "give_final_response":
        return "response"

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
    workflow.add_node("chat_llm_generate_lambda", chat_llm_generate_lambda)
    workflow.add_node("comfort_reply",comfort_reply)
    workflow.add_node("transfer_reply", transfer_reply)
    workflow.add_node("give_rhetorical_question",give_rhetorical_question)
    workflow.add_node("give_tool_response",give_tool_response)
    workflow.add_node("give_response_wo_tool",give_response_without_any_tool)
    workflow.add_node("rag_retrieve_lambda",rag_retrieve_lambda)
    workflow.add_node("rag_llm_lambda",rag_llm_lambda)
    
    # add all edges
    workflow.set_entry_point("query_preprocess_lambda")
    workflow.add_edge("query_preprocess_lambda","intention_detection_lambda")
    workflow.add_edge("tool_execute_lambda","agent_lambda")
    workflow.add_edge("rag_retrieve_lambda","rag_llm_lambda")
    workflow.add_edge("rag_llm_lambda",END)
    workflow.add_edge("comfort_reply",END)
    workflow.add_edge("transfer_reply",END)
    workflow.add_edge("chat_llm_generate_lambda",END)
    workflow.add_edge("give_rhetorical_question",END)
    workflow.add_edge("give_tool_response",END)
    workflow.add_edge("give_response_wo_tool",END)

    # add conditional edges
    workflow.add_conditional_edges(
        "intention_detection_lambda",
        intent_route,
        {
            "comfort": "comfort_reply",
            "transfer": "transfer_reply",
            "chat": "chat_llm_generate_lambda",
            "other": "agent_lambda",
            "qa": "rag_retrieve_lambda"
        }
    )

    workflow.add_conditional_edges(
        "agent_lambda",
        agent_route,
        {
            "no tool": "give_response_wo_tool",
            "rhetorical question": "give_rhetorical_question",
            "response": "give_tool_response",
            "continue":"tool_execute_lambda"
        }
    )
    app = workflow.compile()
    return app

app = None 

def common_entry(event_body):
    """
    Entry point for the Lambda function.
    :param event_body: The event body for lambda function.
    return: answer(str)
    """
    global app 
    if app is None:
        app = build_graph()
     

    # debuging
    # with open('common_entry_workflow.png','wb') as f:
    #     f.write(app.get_graph().draw_png())
    
    ################################################################################
    # prepare inputs and invoke graph
    event_body['chatbot_config'] = parse_common_entry_config(event_body['chatbot_config'])
    
    query = event_body['query']
    chat_history = event_body['chat_history']
    stream = event_body['stream']
    message_id = event_body['custom_message_id']
    ws_connection_id = event_body['ws_connection_id']
    
    # invoke graph and get results
    response = app.invoke({
        "stream":stream,
        "chatbot_config": event_body['chatbot_config'],
        "query":query,
        "trace_infos": [],
        "message_id": message_id,
        "chat_history": chat_history,
        "agent_chat_history": chat_history + [{"role":"user","content":query}],
        "ws_connection_id":ws_connection_id,
        "debug_infos": {},
        "extra_response": {}
    })

    return {"answer":response['answer'],**response["extra_response"]}

main_chain_entry = common_entry