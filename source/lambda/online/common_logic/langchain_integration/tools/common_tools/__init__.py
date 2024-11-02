from .. import lazy_tool_load_decorator,ToolIdentifier,ToolManager
from common_logic.common_utils.constant import SceneType


@lazy_tool_load_decorator(SceneType.COMMON,"get_weather")
def _load_weather_tool(tool_identifier:ToolIdentifier):
    from . import get_weather
    tool_def = {
        "description": "Get the current weather for `city_name`",
        "properties": {
            "city_name": {
                "description": "The name of the city to be queried",
                "type": "string"
            },
        },
        "required": ["city_name"]
    }
    ToolManager.register_func_as_tool(
        func=get_weather.get_weather,
        tool_def=tool_def,
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        return_direct=False
    )


@lazy_tool_load_decorator(SceneType.COMMON,"give_rhetorical_question")
def _load_rhetorical_tool(tool_identifier:ToolIdentifier):
    from . import give_rhetorical_question
    tool_def = {
        "description": "If the user's question is not clear and specific, resulting in the inability to call other tools, please call this tool to ask the user a rhetorical question",
        "properties": {
            "question": {
                "description": "The rhetorical question to user",
                "type": "string"
            },
        },
        "required": ["question"]
    } 
    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=give_rhetorical_question.give_rhetorical_question,
        tool_def=tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON,"give_final_response")
def _load_final_response_tool(tool_identifier:ToolIdentifier):
    from . import give_final_response
    
    tool_def = {
        "description": "If none of the other tools need to be called, call the current tool to complete the direct response to the user.",
        "properties": {
            "response": {
                "description": "Response to user",
                "type": "string"
            }
        },
        "required": ["response"]
    }
    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=give_final_response.give_final_response,
        tool_def=tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON,"chat")
def _load_chat_tool(tool_identifier:ToolIdentifier):
    from . import chat
    tool_def = {
        "description": "casual talk with AI",
        "properties": {
            "response": {
                "description": "response to users",
                "type": "string"
                }
        },
        "required": ["response"]
    }

    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=chat.chat,
        tool_def=tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON,"rag_tool")
def _load_rag_tool(tool_identifier:ToolIdentifier):
    from . import rag
    tool_def = {
        "description": "private knowledge",
        "properties": {
            "query": {
                "description": "query for retrieve",
                "type": "string"
                }
        },
        # "required": ["query"]
    }
    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=rag.rag_tool,
        tool_def=tool_def,
        return_direct=True
    )



################### langchain tools #######################

@lazy_tool_load_decorator(SceneType.COMMON,"python_repl")
def _loadd_python_repl_tool(tool_identifier:ToolIdentifier):
    from langchain_core.tools import Tool
    from langchain_experimental.utilities import PythonREPL
    python_repl = PythonREPL()
    repl_tool = Tool(
        name="python_repl",
        description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you SHOULD print it out with `print(...)`.",
        func=python_repl.run
    )
    ToolManager.register_lc_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        tool=repl_tool
    )

