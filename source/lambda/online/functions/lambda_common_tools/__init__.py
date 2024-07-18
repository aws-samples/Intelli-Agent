from common_logic.common_utils.constant import SceneType,ToolRuningMode
from .._tool_base import tool_manager 
from . import (
    get_weather,
    give_rhetorical_question,
    give_final_response,
    chat,
    knowledge_base_retrieve,
    rag
)


SCENE = SceneType.COMMON  
LAMBDA_NAME = "lambda_common_tools"

tool_manager.register_tool({
    "name": "get_weather",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": get_weather.lambda_handler,
    "tool_def":{
            "name": "get_weather",
            "description": "Get the current weather for `city_name`",
            "parameters": {
                "type": "object",
                "properties": {
                "city_name": {
                    "description": "The name of the city to be queried",
                    "type": "string"
                }, 
                },
                "required": ["city_name"]
            }
        },
    "running_mode": ToolRuningMode.LOOP
    }
)


tool_manager.register_tool(
    {
        "name":"give_rhetorical_question",
        "scene": SCENE,
        "lambda_name": LAMBDA_NAME,
        "lambda_module_path": give_rhetorical_question.lambda_handler,
        "tool_def":{
                "name": "give_rhetorical_question",
                "description": "If the user's question is not clear and specific, resulting in the inability to call other tools, please call this tool to ask the user a rhetorical question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "description": "The rhetorical question to user",
                            "type": "string"
                    },
                    },
                    "required": ["question"],
                },
            },
        "running_mode": ToolRuningMode.ONCE
    }
)


tool_manager.register_tool(
    {
        "name": "give_final_response",
        "scene": SCENE,
        "lambda_name": LAMBDA_NAME,
        "lambda_module_path": give_final_response.lambda_handler,
        "tool_def":{
                "name": "give_final_response",
                "description": "If none of the other tools need to be called, call the current tool to complete the direct response to the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "description": "Response to user",
                            "type": "string"
                    }
                    },
                    "required": ["response"]
                },
            },
         "running_mode": ToolRuningMode.ONCE
    }
)


tool_manager.register_tool({
    "name": "chat",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": chat.lambda_handler,
    "tool_def":{
        "name": "chat",
        "description": "casual talk with AI",
        "parameters": {
            "type": "object",
            "properties": {
                "response": {
                    "description": "response to users",
                    "type": "string"
            }},
            "required": ["response"]
        },
    },
    "running_mode": ToolRuningMode.ONCE
})

tool_manager.register_tool({
    "name":"knowledge_base_retrieve",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": knowledge_base_retrieve.lambda_handler,
    "tool_def":{
        "name": "knowledge_base_retrieve",
        "description": "retrieve domain knowledge",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "description": "query for retrieve",
                    "type": "string"
            }},
            "required": ["query"]
        },
    },
    "running_mode": ToolRuningMode.LOOP
})


tool_manager.register_tool({
    "name": "rag_tool",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": rag.lambda_handler,
    "tool_def":{
        "name": "rag_tool",
        "description": "private knowledge",
        "parameters": {}
    },
    "running_mode": ToolRuningMode.ONCE
})

tool_manager.register_tool({
    "name": "rag_bedrock_tool",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": rag.lambda_handler,
    "tool_def":{
        "name": "rag_bedrock_tool",
        "description": "knowledge about Amazon Bedrock. Amazon Bedrock is a fully managed service that offers a choice of high-performing foundation models (FMs) from leading AI companies like AI21 Labs, Anthropic, Cohere, Meta, Mistral AI, Stability AI, and Amazon through a single API, along with a broad set of capabilities you need to build generative AI applications with security, privacy, and responsible AI.",
        "parameters": {}
    },
    "running_mode": ToolRuningMode.ONCE
})

tool_manager.register_tool({
    "name": "rag_s3_tool",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": rag.lambda_handler,
    "tool_def":{
        "name": "rag_s3_tool",
        "description": "knowledge about Amazon Bedrock. Amazon Bedrock is a fully managed service that offers a choice of high-performing foundation models (FMs) from leading AI companies like AI21 Labs, Anthropic, Cohere, Meta, Mistral AI, Stability AI, and Amazon through a single API, along with a broad set of capabilities you need to build generative AI applications with security, privacy, and responsible AI.",
        "parameters": {}
    },
    "running_mode": ToolRuningMode.ONCE
})







