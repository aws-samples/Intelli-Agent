import json
from langgraph.graph import StateGraph,END
from common_logic.common_utils.lambda_invoke_utils import invoke_lambda,node_monitor_wrapper

from functions.tool_calling_parse import parse_tool_calling as _parse_tool_calling
from common_logic.common_utils.lambda_invoke_utils import send_trace
from common_logic.common_utils.exceptions import (
    ToolNotExistError,
    ToolParameterNotExistError,
    MultipleToolNameError,
    ToolNotFound
)
from common_logic.common_utils.logger_utils import get_logger
from functions.tool_execute_result_format import format_tool_call_results

logger = get_logger("agent_base")

@node_monitor_wrapper
def tools_choose_and_results_generation(state):
    # check once tool calling
    agent_current_output:dict = invoke_lambda(
        event_body={
            **state
            },
        lambda_name="Online_Agent",
        lambda_module_path="lambda_agent.agent",
        handler_name="lambda_handler"
    )
    agent_current_call_number = state['agent_current_call_number'] + 1
    agent_repeated_call_validation = state['agent_current_call_number'] < state['agent_repeated_call_limit']

    send_trace(f"\n\n**agent_current_output:** \n{json.dumps(agent_current_output['agent_output'],ensure_ascii=False,indent=2)}\n\n **agent_current_call_number:** {agent_current_call_number}", state["stream"], state["ws_connection_id"])
    return {
        "agent_current_output": agent_current_output,
        "agent_current_call_number": agent_current_call_number,
        "agent_repeated_call_validation": agent_repeated_call_validation
    }


@node_monitor_wrapper
def results_evaluation(state):
    # parse tool_calls:
    try:
        output = _parse_tool_calling(
            agent_output=state['agent_current_output']
        )
        tool_calls = output['tool_calls']
        send_trace(f"\n\n**tool_calls parsed:** \n{tool_calls}", state["stream"], state["ws_connection_id"], state["enable_trace"])
        if not state["extra_response"].get("current_agent_intent_type", None):
            state["extra_response"]["current_agent_intent_type"] = output['tool_calls'][0]["name"]
       
        return {
            "function_calling_parse_ok": True,
            "function_calling_parsed_tool_calls": tool_calls,
            "agent_tool_history": [output['agent_message']]
        }
    
    except (ToolNotExistError,
             ToolParameterNotExistError,
             MultipleToolNameError,
             ToolNotFound
             ) as e:
        send_trace(f"\n\n**tool_calls parse failed:** \n{str(e)}", state["stream"], state["ws_connection_id"], state["enable_trace"])
        return {
            "function_calling_parse_ok": False,
            "agent_tool_history":[
                e.agent_message,
                e.error_message
            ]
        }


@node_monitor_wrapper
def tool_execution(state):
    """executor lambda
    Args:
        state (NestUpdateState): _description_

    Returns:
        _type_: _description_
    """
    tool_calls = state['function_calling_parsed_tool_calls']
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
        "agent_tool_history": [output['tool_message']]
        }



def build_agent_graph(chatbot_state_cls):
    def _results_evaluation_route(state: dict):
        #TODO: pass no need tool calling or valid tool calling?
        if state["agent_repeated_call_validation"] and not state["function_calling_parse_ok"]:
            return "invalid tool calling"
        return "continue"

    workflow = StateGraph(chatbot_state_cls)
    workflow.add_node("tools_choose_and_results_generation", tools_choose_and_results_generation)
    workflow.add_node("results_evaluation", results_evaluation)

    # add all edges
    workflow.set_entry_point("tools_choose_and_results_generation")
    workflow.add_edge("tools_choose_and_results_generation","results_evaluation")

    # add conditional edges
    # the results of agent planning will be evaluated and decide next step:
    # 1. invalid tool calling: if agent makes clear mistakes, like wrong tool names or format, it will be forced to plan again
    # 2. valid tool calling: the agent chooses the valid tools
    workflow.add_conditional_edges(
        "results_evaluation",
        _results_evaluation_route,
        {
            "invalid tool calling": "tools_choose_and_results_generation",
            "continue": END,
        }
    )
    app = workflow.compile()
    return app