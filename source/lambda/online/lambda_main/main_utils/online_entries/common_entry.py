import json
from typing import Annotated, Any, TypedDict

from common_utils.constant import LLMTaskType
from common_utils.exceptions import (
    ToolNotExistError, 
    ToolParameterNotExistError,
    MultipleToolNameError,
    ToolNotFound
)
from common_utils.time_utils import get_china_now
from common_utils.lambda_invoke_utils import (
    invoke_lambda,
    is_running_local,
    node_monitor_wrapper,
    send_trace,
)
from common_utils.python_utils import add_messages, update_nest_dict
from common_utils.logger_utils import get_logger
from common_utils.serialization_utils import JSONEncoder
from functions.tool_calling_parse import parse_tool_calling as _parse_tool_calling
from functions.tool_execute_result_format import format_tool_call_results
from functions.tools import Tool, get_tool_by_name
from lambda_main.main_utils.parse_config import parse_common_entry_config
from langgraph.graph import END, StateGraph


logger = get_logger('common_entry')

class ChatbotState(TypedDict):
    chatbot_config: dict  # chatbot config
    query: str
    ws_connection_id: str
    stream: bool
    query_rewrite: str = None  # query rewrite ret
    intent_type: str = None  # intent
    intention_fewshot_examples: list
    trace_infos: Annotated[list[str], add_messages]
    message_id: str = None
    chat_history: Annotated[list[dict], add_messages]
    agent_chat_history: Annotated[list[dict], add_messages]
    current_function_calls: list[str]
    current_tool_execute_res: dict
    debug_infos: Annotated[dict, update_nest_dict]
    answer: Any  # final answer
    current_monitor_infos: str
    extra_response: Annotated[dict, update_nest_dict]
    contexts: str = None
    all_index_retriever_contexts: list
    current_intent_tools: list  #
    current_tool_calls: list
    current_agent_tools_def: list[dict]
    current_agent_model_id: str
    current_agent_output: dict
    parse_tool_calling_ok: bool
    enable_trace: bool
    agent_recursion_limit: int # agent recursion limit
    current_agent_recursion_num: int
    format_intention: str

def get_common_system_prompt():
    now = get_china_now()
    date_str = now.strftime("%Y年%m月%d日")
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekdays[now.weekday()]
    system_prompt = f"你是一个亚马逊云科技的AI助理，你的名字是亚麻小Q。今天是{date_str},{weekday}. "
    return system_prompt

####################
# nodes in lambdas #
####################


@node_monitor_wrapper
def query_preprocess_lambda(state: ChatbotState):
    output: str = invoke_lambda(
        event_body=state,
        lambda_name="Online_Query_Preprocess",
        lambda_module_path="lambda_query_preprocess.query_preprocess",
        handler_name="lambda_handler",
    )
    send_trace(f"\n\n**query_rewrite:** \n{output}", state["stream"], state["ws_connection_id"], state["enable_trace"])
    return {"query_rewrite": output}


@node_monitor_wrapper
def intention_detection_lambda(state: ChatbotState):
    intention_fewshot_examples = invoke_lambda(
        lambda_module_path="lambda_intention_detection.intention",
        lambda_name="Online_Intention_Detection",
        handler_name="lambda_handler",
        event_body=state,
    )

    # send trace
    send_trace(
        f"**intention retrieved:**\n{json.dumps(intention_fewshot_examples,ensure_ascii=False,indent=2)}", state["stream"], state["ws_connection_id"], state["enable_trace"])
    current_intent_tools: list[str] = list(
        set([e["intent"] for e in intention_fewshot_examples])
    )
    return {
        "intention_fewshot_examples": intention_fewshot_examples,
        "current_intent_tools": current_intent_tools,
        "intent_type": "other",
    }



# @node_monitor_wrapper
# def rag_all_index_lambda(state: ChatbotState):
#     # call retrivever
#     retriever_params = state["chatbot_config"]["all_index_retriever_config"]
#     retriever_params["query"] = state["query"]
#     output: str = invoke_lambda(
#         event_body=retriever_params,
#         lambda_name="Online_Function_Retriever",
#         lambda_module_path="functions.lambda_retriever.retriever",
#         handler_name="lambda_handler",
#     )
#     contexts = [doc["page_content"] for doc in output["result"]["docs"]]
#     send_trace("**all index retriever lambda result** \n" + ("\n"+"="*50 + "\n").join(contexts))
#     return {"all_index_retriever_contexts": contexts}


@node_monitor_wrapper
def agent_lambda(state: ChatbotState):
    system_prompt = get_common_system_prompt()
    # all_index_retriever_contexts = state.get("all_index_retriever_contexts",[])
    all_index_retriever_contexts = state.get("contexts",[])
    if all_index_retriever_contexts:
        context = '\n\n'.join(all_index_retriever_contexts)
        system_prompt += f"\n下面有一些背景信息供参考:\n<context>\n{context}\n</context>\n"
    current_agent_output:dict = invoke_lambda(
        event_body={
            **state,
            "chat_history":state['agent_chat_history'],
            "other_chain_kwargs": {"system_prompt": get_common_system_prompt()}
            },
        lambda_name="Online_Agent",
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler",
   
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
    
    output = format_tool_call_results(tool_calls[0]['model_id'],tool_call_results)
    send_trace(f'**tool_execute_res:** \n{output["tool_message"]["content"]}')
    return {"agent_chat_history": [output['tool_message']]}


@node_monitor_wrapper
def rag_all_index_lambda(state: ChatbotState):
    # call retrivever
    retriever_params = state["chatbot_config"]["rag_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler",
    )
    contexts = [doc["page_content"] for doc in output["result"]["docs"]]
    return {"contexts": contexts}


@node_monitor_wrapper
def rag_llm_lambda(state: ChatbotState):
    output: str = invoke_lambda(
        lambda_name="Online_LLM_Generate",
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name="lambda_handler",
        event_body={
            "llm_config": {
                **state["chatbot_config"]["rag_config"]["llm_config"],
                "stream": state["stream"],
                "intent_type": LLMTaskType.RAG,
            },
            "llm_input": {
                "contexts": [state["contexts"]],
                "query": state["query"],
                "chat_history": state["chat_history"],
            },
        },
    )
    return {"answer": output}

@node_monitor_wrapper
def aws_qa_lambda(state: ChatbotState):
    # call retrivever
    retriever_params = state["chatbot_config"]["aws_qa_config"]["retriever_config"]
    retriever_params["query"] = state["query"]
    output: str = invoke_lambda(
        event_body=retriever_params,
        lambda_name="Online_Function_Retriever",
        lambda_module_path="functions.lambda_retriever.retriever",
        handler_name="lambda_handler",
    )
    contexts = [doc["page_content"] for doc in output["result"]["docs"]]
    return {"contexts": contexts}

@node_monitor_wrapper
def chat_llm_generate_lambda(state: ChatbotState):
    answer: dict = invoke_lambda(
        event_body={
            "llm_config": {
                **state["chatbot_config"]["chat_config"],
                "stream": state["stream"],
                "intent_type": LLMTaskType.CHAT,
                "system_prompt": get_common_system_prompt()
            },
            "llm_input": {
                "query": state["query"],
                "chat_history": state["chat_history"],
               
            },
        },
        lambda_name="Online_LLM_Generate",
        lambda_module_path="lambda_llm_generate.llm_generate",
        handler_name="lambda_handler",
    )
    return {"answer": answer}


def format_reply(state: ChatbotState):
    recent_tool_name = state["current_tool_calls"][0]
    if recent_tool_name == 'comfort':
        return {"answer": "不好意思没能帮到您，是否帮你转人工客服？"}
    if recent_tool_name == 'transfer':
        return {"answer": "立即为您转人工客服，请稍后"}

def give_rhetorical_question(state: ChatbotState):
    recent_tool_calling: list[dict] = state["current_tool_calls"][0]
    return {"answer": recent_tool_calling["kwargs"]["question"]}


def give_final_response(state: ChatbotState):
    recent_tool_calling: list[dict] = state["current_tool_calls"][0]
    return {"answer": recent_tool_calling["kwargs"]["response"]}


def qq_matched_reply(state: ChatbotState):
    return {"answer": state["answer"]}


################
# define edges #
################


def query_route(state: dict):
    return state["chatbot_config"]["chatbot_mode"]


def intent_route(state: dict):
    if not state['intention_fewshot_examples']:
        state['extra_response']['current_agent_intent_type'] = 'final_rag'
        return 'no fewshot examples'
    return state["intent_type"]


def agent_route(state: dict):
    parse_tool_calling_ok = state["parse_tool_calling_ok"]
    if not parse_tool_calling_ok:
        if state['current_agent_recursion_num'] >= state['agent_recursion_limit']:
            send_trace(f"Reach the agent recursion limit: {state['agent_recursion_limit']}, route to final rag")
            return 'first final response/rag intention/recursion limit'
        return "invalid tool calling"

    recent_tool_calls: list[dict] = state["current_tool_calls"]

    if not recent_tool_calls:
        return "no tool"

    recent_tool_call = recent_tool_calls[0]

    recent_tool_name = recent_tool_call["name"]

    if recent_tool_name in ["comfort", "transfer"]:
        return "format reply"

    if recent_tool_name in ["QA", "service_availability", "explain_abbr"]:
        return "aws qa"

    if recent_tool_name in ["assist", "chat"]:
        return "chat"

    if recent_tool_call["name"] == "give_rhetorical_question":
        return "rhetorical question"

    if recent_tool_call["name"] == "give_final_response":
        if state['current_agent_recursion_num'] == 1:
            return "first final response/rag intention/recursion limit"
        else:
            return "give final response"
    
    if state['current_agent_recursion_num'] >= state['agent_recursion_limit']:
        send_trace(f"Reach the agent recursion limit: {state['agent_recursion_limit']}, route to final rag")
        return 'first final response/rag intention/recursion limit'

    return "continue"

def rag_all_index_lambda_route(state: dict):
    if not state.get('intention_fewshot_examples',[]) and state['current_agent_recursion_num'] == 0:
        return "no intention detected"
    else:
        return "rag model/first final response/rag intention/recursion limit"


#############################
# define whole online graph #
#############################


def build_graph():
    workflow = StateGraph(ChatbotState)
    # add all nodes
    workflow.add_node("query_preprocess_lambda", query_preprocess_lambda)
    workflow.add_node("intention_detection_lambda", intention_detection_lambda)
    workflow.add_node("rag_all_index_lambda", rag_all_index_lambda)
    workflow.add_node("agent_lambda", agent_lambda)
    workflow.add_node("tool_execute_lambda", tool_execute_lambda)
    workflow.add_node("chat_llm_generate_lambda", chat_llm_generate_lambda)
    workflow.add_node("format_reply", format_reply)
    # workflow.add_node("comfort_reply", comfort_reply)
    # workflow.add_node("transfer_reply", transfer_reply)
    workflow.add_node("give_rhetorical_question", give_rhetorical_question)
    workflow.add_node("give_final_response", give_final_response)
    # workflow.add_node("give_response_wo_tool", give_response_without_any_tool)
    # workflow.add_node("rag_all_index_lambda", rag_all_index_lambda)
    workflow.add_node("aws_qa_lambda", aws_qa_lambda)
    workflow.add_node("rag_llm_lambda", rag_llm_lambda)
    workflow.add_node("qq_matched_reply", qq_matched_reply)
    workflow.add_node("parse_tool_calling", parse_tool_calling)

    # add all edges
    workflow.set_entry_point("query_preprocess_lambda")
    # workflow.add_edge("query_preprocess_lambda","intention_detection_lambda")
    # workflow.add_edge("intention_detection_lambda", "agent_lambda")
    # workflow.add_edge("rag_all_index_lambda","agent_lambda")
    workflow.add_edge("tool_execute_lambda", "agent_lambda")
    # workflow.add_edge("rag_all_index_lambda", "rag_llm_lambda")
    workflow.add_edge("aws_qa_lambda", "rag_llm_lambda")
    workflow.add_edge("agent_lambda", "parse_tool_calling")
    workflow.add_edge("rag_llm_lambda", END)
    workflow.add_edge("format_reply", END)
    # workflow.add_edge("comfort_reply", END)
    # workflow.add_edge("transfer_reply", END)
    workflow.add_edge("chat_llm_generate_lambda", END)
    workflow.add_edge("give_rhetorical_question", END)
    workflow.add_edge("give_final_response", END)
    # workflow.add_edge("give_response_wo_tool", END)
    # workflow.add_edge("rag_all_index_lambda", "rag_llm_lambda")
    workflow.add_edge("rag_llm_lambda", END)
    workflow.add_edge("qq_matched_reply", END)

    # add conditional edges
    workflow.add_conditional_edges(
        "query_preprocess_lambda",
        query_route,
        {
            "chat": "chat_llm_generate_lambda",
            "rag": "rag_all_index_lambda",
            "agent": "intention_detection_lambda",
        },
    )

    # add conditional edges
    workflow.add_conditional_edges(
        "intention_detection_lambda",
        intent_route,
        {
            "other": "agent_lambda",
            "qq_mathed": "qq_matched_reply",
            "no fewshot examples": "rag_all_index_lambda"
        },
    )

    workflow.add_conditional_edges(
        "parse_tool_calling",
        agent_route,
        {
            "invalid tool calling": "agent_lambda",
            "give final response": "give_final_response",
            "rhetorical question": "give_rhetorical_question",
            "format reply": "format_reply",
            # "comfort": "comfort_reply",
            # "transfer": "transfer_reply",
            "chat": "chat_llm_generate_lambda",
            "aws qa": "aws_qa_lambda",
            "continue": "tool_execute_lambda",
            "first final response/rag intention/recursion limit": "rag_all_index_lambda",
        },
    )

    workflow.add_conditional_edges(
        "rag_all_index_lambda",
        rag_all_index_lambda_route,
        {
            "no intention detected": "agent_lambda",
            "rag model/first final response/rag intention/recursion limit": "rag_llm_lambda",
        },
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
    # TODO only write when run local
    if is_running_local():
        with open("common_entry_workflow.png", "wb") as f:
            f.write(app.get_graph().draw_png())

    ################################################################################
    # prepare inputs and invoke graph
    event_body["chatbot_config"] = parse_common_entry_config(
        event_body["chatbot_config"]
    )
    logger.info(f'event_body:\n{json.dumps(event_body,ensure_ascii=False,indent=2,cls=JSONEncoder)}')
    chatbot_config = event_body["chatbot_config"]
    query = event_body["query"]
    use_history = chatbot_config["use_history"]
    chat_history = event_body["chat_history"] if use_history else []
    stream = event_body["stream"]
    message_id = event_body["custom_message_id"]
    ws_connection_id = event_body["ws_connection_id"]
    enable_trace = chatbot_config["enable_trace"]

    # invoke graph and get results
    response = app.invoke(
        {
            "stream": stream,
            "chatbot_config": chatbot_config,
            "query": query,
            "enable_trace": enable_trace,
            "trace_infos": [],
            "message_id": message_id,
            "chat_history": chat_history,
            "agent_chat_history": chat_history + [{"role": "user", "content": query}],
            "ws_connection_id": ws_connection_id,
            "debug_infos": {},
            "extra_response": {},
            "agent_recursion_limit": chatbot_config['agent_recursion_limit'],
            "current_agent_recursion_num": 0,
        }
    )

    return {"answer": response["answer"], **response["extra_response"]}


main_chain_entry = common_entry
