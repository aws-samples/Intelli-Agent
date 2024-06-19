import json
from typing import Annotated, Any, TypedDict

from common_utils.constant import LLMTaskType
from common_utils.exceptions import ToolNotExistError, ToolParameterNotExistError
from common_utils.lambda_invoke_utils import (
    invoke_lambda,
    is_running_local,
    node_monitor_wrapper,
    send_trace,
)
from common_utils.python_utils import add_messages, update_nest_dict
from functions.tool_calling_parse import parse_tool_calling as _parse_tool_calling
from functions.tool_execute_result_format import format_tool_execute_result
from functions.tools import Tool, get_tool_by_name
from lambda_main.main_utils.parse_config import parse_common_entry_config
from langgraph.graph import END, StateGraph


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
    current_intent_tools: list  #
    current_tool_calls: list
    current_agent_tools_def: list[dict]
    current_agent_model_id: str
    parse_tool_calling_ok: bool
    enable_trace: bool


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
    send_trace(
        f"\n\n**query_rewrite:** \n{output}",
        state["stream"],
        state["ws_connection_id"],
        state["enable_trace"],
    )
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
        f"**intention retrieved:**\n{json.dumps(intention_fewshot_examples,ensure_ascii=False,indent=2)}",
        state["stream"],
        state["ws_connection_id"],
        state["enable_trace"],
    )
    current_intent_tools: list[str] = list(
        set([e["intent"] for e in intention_fewshot_examples])
    )
    return {
        "intention_fewshot_examples": intention_fewshot_examples,
        "current_intent_tools": current_intent_tools,
        "intent_type": "other",
    }


@node_monitor_wrapper
def agent_lambda(state: ChatbotState):
    output: dict = invoke_lambda(
        event_body={**state, "chat_history": state["agent_chat_history"]},
        lambda_name="Online_Agent",
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler",
    )
    current_function_calls = output["function_calls"]
    content = output["content"]
    current_agent_tools_def = output["current_agent_tools_def"]
    current_agent_model_id = output["current_agent_model_id"]
    send_trace(
        f"\n\n**current_function_calls:** \n{current_function_calls},\n**model_id:** \n{current_agent_model_id}\n**ai content:** \n{content}",
        state["stream"],
        state["ws_connection_id"],
        state["enable_trace"],
    )
    return {
        "current_agent_model_id": current_agent_model_id,
        "current_function_calls": current_function_calls,
        "current_agent_tools_def": current_agent_tools_def,
        "agent_chat_history": [{"role": "ai", "content": content}],
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
        tool_calls = _parse_tool_calling(
            model_id=state["current_agent_model_id"],
            function_calls=state["current_function_calls"],
            tools=state["current_agent_tools_def"],
        )
        send_trace(
            f"\n\n**tool_calls parsed:** \n{tool_calls}",
            state["stream"],
            state["ws_connection_id"],
            state["enable_trace"],
        )
        if tool_calls:
            state["extra_response"]["current_agent_intent_type"] = tool_calls[0]["name"]
        else:
            tool_format = (
                "<function_calls>\n"
                "<invoke>\n"
                "<tool_name>$TOOL_NAME</tool_name>\n"
                "<parameters>\n"
                "<$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>\n"
                "...\n"
                "</parameters>\n"
                "</invoke>\n"
                "</function_calls>\n"
            )
            return {
                "parse_tool_calling_ok": False,
                "agent_chat_history": [
                    {
                        "role": "user",
                        # "content": f"当前没有解析到tool,请检查tool调用的格式是否正确，并重新输出某个tool的调用。注意正确的tool调用格式应该为: {tool_format}。\n如果你认为当前不需要调用其他工具，请直接调用“give_final_response”工具进行返回。"
                        "content": f"\n如果你认为当前不需要调用其他工具，请直接调用“QA”工具进行返回。",
                    }
                ],
            }

        return {
            "parse_tool_calling_ok": True,
            "current_tool_calls": tool_calls,
        }
    except (ToolNotExistError, ToolParameterNotExistError) as e:
        send_trace(
            f"\n\n**tool_calls parse failed:** \n{str(e)}",
            state["stream"],
            state["ws_connection_id"],
            state["enable_trace"],
        )
        return {
            "parse_tool_calling_ok": False,
            "agent_chat_history": [
                {
                    "role": "user",
                    "content": format_tool_execute_result(
                        model_id=state["current_agent_model_id"],
                        tool_output={
                            "code": 1,
                            "result": e.to_agent(),
                            "tool_name": e.tool_name,
                        },
                    ),
                }
            ],
        }


@node_monitor_wrapper
def tool_execute_lambda(state: ChatbotState):
    tool_calls = state["current_tool_calls"]
    assert len(tool_calls) == 1, tool_calls
    tool_call_results = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        event_body = tool_call["kwargs"]
        tool: Tool = get_tool_by_name(tool_name)
        # call tool
        output: dict = invoke_lambda(
            event_body=event_body,
            lambda_name=tool.lambda_name,
            lambda_module_path=tool.lambda_module_path,
            handler_name=tool.handler_name,
        )

        tool_call_results.append(
            {
                "name": tool_name,
                "output": output,
                "kwargs": tool_call["kwargs"],
                "model_id": tool_call["model_id"],
            }
        )

    # convert tool calling as chat history
    tool_call_result_strs = []
    for tool_call_result in tool_call_results:
        tool_exe_output = tool_call_result["output"]
        tool_exe_output["tool_name"] = tool_call_result["name"]
        ret: str = format_tool_execute_result(
            tool_call_result["model_id"], tool_exe_output
        )
        tool_call_result_strs.append(ret)

    ret = "\n".join(tool_call_result_strs)
    send_trace(
        f"\n\n**tool execute result:** \n{ret}",
        state["stream"],
        state["ws_connection_id"],
        state["enable_trace"],
    )
    return {"agent_chat_history": [{"role": "user", "content": ret}]}


@node_monitor_wrapper
def rag_retrieve_lambda(state: ChatbotState):
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
def chat_llm_generate_lambda(state: ChatbotState):
    answer: dict = invoke_lambda(
        event_body={
            "llm_config": {
                **state["chatbot_config"]["chat_config"],
                "stream": state["stream"],
                "intent_type": LLMTaskType.CHAT,
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


def comfort_reply(state: ChatbotState):
    return {"answer": "不好意思没能帮到您，是否帮你转人工客服？"}


def transfer_reply(state: ChatbotState):
    return {"answer": "立即为您转人工客服，请稍后"}


def give_rhetorical_question(state: ChatbotState):
    recent_tool_calling: list[dict] = state["current_tool_calls"][0]
    return {"answer": recent_tool_calling["kwargs"]["question"]}


# def no_available_tool(state: ChatbotState):
#     recent_tool_calling: list[dict] = state["current_tool_calls"][0]
#     return {"answer": recent_tool_calling["kwargs"]["response"]}


def give_final_response(state: ChatbotState):
    recent_tool_calling: list[dict] = state["current_tool_calls"][0]
    return {"answer": recent_tool_calling["kwargs"]["response"]}


# def give_response_without_any_tool(state: ChatbotState):
#     chat_history = state["agent_chat_history"]
#     return {"answer": chat_history[-1]["content"]}


def qq_matched_reply(state: ChatbotState):
    return {"answer": state["answer"]}


################
# define edges #
################


def query_route(state: dict):
    return state["chatbot_config"]["chatbot_mode"]


def intent_route(state: dict):
    return state["intent_type"]


def agent_route(state: dict):
    parse_tool_calling_ok = state["parse_tool_calling_ok"]
    if not parse_tool_calling_ok:
        return "invalid tool calling"

    recent_tool_calls: list[dict] = state["current_tool_calls"]

    if not recent_tool_calls:
        return "no tool"

    recent_tool_call = recent_tool_calls[0]

    recent_tool_name = recent_tool_call["name"]

    if recent_tool_name in ["comfort", "transfer", "chat"]:
        return recent_tool_name

    if recent_tool_name == "QA":
        return "aws_qa"

    if recent_tool_name == "assist":
        return "chat"

    if recent_tool_call["name"] == "give_rhetorical_question":
        return "rhetorical question"

    if recent_tool_call["name"] == "give_final_response":
        return "give final response"

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
    workflow.add_node("comfort_reply", comfort_reply)
    workflow.add_node("transfer_reply", transfer_reply)
    workflow.add_node("give_rhetorical_question", give_rhetorical_question)
    workflow.add_node("give_final_response", give_final_response)
    # workflow.add_node("give_response_wo_tool", give_response_without_any_tool)
    workflow.add_node("rag_retrieve_lambda", rag_retrieve_lambda)
    workflow.add_node("aws_qa_lambda", aws_qa_lambda)
    workflow.add_node("rag_llm_lambda", rag_llm_lambda)
    workflow.add_node("qq_matched_reply", qq_matched_reply)
    workflow.add_node("parse_tool_calling", parse_tool_calling)

    # add all edges
    workflow.set_entry_point("query_preprocess_lambda")
    # workflow.add_edge("query_preprocess_lambda","intention_detection_lambda")
    workflow.add_edge("intention_detection_lambda", "agent_lambda")
    workflow.add_edge("tool_execute_lambda", "agent_lambda")
    workflow.add_edge("rag_retrieve_lambda", "rag_llm_lambda")
    workflow.add_edge("aws_qa_lambda", "rag_llm_lambda")
    workflow.add_edge("agent_lambda", "parse_tool_calling")
    workflow.add_edge("rag_llm_lambda", END)
    workflow.add_edge("comfort_reply", END)
    workflow.add_edge("transfer_reply", END)
    workflow.add_edge("chat_llm_generate_lambda", END)
    workflow.add_edge("give_rhetorical_question", END)
    workflow.add_edge("give_final_response", END)
    # workflow.add_edge("give_response_wo_tool", END)
    workflow.add_edge("rag_retrieve_lambda", "rag_llm_lambda")
    workflow.add_edge("rag_llm_lambda", END)
    workflow.add_edge("qq_matched_reply", END)

    # add conditional edges
    workflow.add_conditional_edges(
        "query_preprocess_lambda",
        query_route,
        {
            "chat": "chat_llm_generate_lambda",
            "rag": "rag_retrieve_lambda",
            "agent": "intention_detection_lambda",
        },
    )

    # add conditional edges
    workflow.add_conditional_edges(
        "intention_detection_lambda",
        intent_route,
        {"other": "agent_lambda", "qq_mathed": "qq_matched_reply"},
    )

    workflow.add_conditional_edges(
        "parse_tool_calling",
        agent_route,
        {
            "invalid tool calling": "agent_lambda",
            "give final response": "give_final_response",
            "rhetorical question": "give_rhetorical_question",
            "comfort": "comfort_reply",
            "transfer": "transfer_reply",
            "chat": "chat_llm_generate_lambda",
            "rag": "rag_retrieve_lambda",
            "aws_qa": "aws_qa_lambda",
            "continue": "tool_execute_lambda",
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
        }
    )

    return {"answer": response["answer"], **response["extra_response"]}


main_chain_entry = common_entry
