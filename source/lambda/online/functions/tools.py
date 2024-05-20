from langchain.pydantic_v1 import BaseModel,Field
from enum import Enum

class ToolDefType(Enum):
    openai = "openai"

class Tool(BaseModel):
    name: str = Field(description="tool name")
    lambda_name: str = Field(description="lambda name")
    lambda_module_path: str = Field(description="local module path")
    handler_name:str = Field(description="local handler name", default="lambda_handler")
    tool_def: dict = Field(description="tool definition")
    tool_def_type: ToolDefType = Field(description="tool definition type",default=ToolDefType.openai.value)
    

class ToolManager:
    def __init__(self) -> None:
        self.tools = {}
    
    def register_tool(self,tool_info:dict):
        tool = Tool(**tool_info)
        assert tool.tool_def_type == ToolDefType.openai.value, f"tool_def_type: {tool.tool_def_type} not support"
        self.tools[tool.name] = tool

    def get_tool_by_name(self,name):
        return self.tools[name]

tool_manager = ToolManager()
get_tool_by_name = tool_manager.get_tool_by_name

tool_manager.register_tool({
    "name": "get_weather",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.lambda_get_weather.get_weather",
    "tool_def":{
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                "location": {
                    "description": "The city and state, e.g. San Francisco, CA",
                    "type": "string"
                },
                "unit": {
                    "description": "The unit of temperature",
                    "allOf": [
                    {
                        "title": "Unit",
                        "description": "An enumeration.",
                        "enum": [
                        "celsius",
                        "fahrenheit"
                        ]
                    }
                    ]
                }
                },
                "required": [
                "location",
                "unit"
                ]
            }
        }
    }
)


tool_manager.register_tool(
    {
        "name":"give_rhetorical_question",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.lambda_give_rhetorical_question.give_rhetorical_question",
        "tool_def":{
                "name": "give_rhetorical_question",
                "description": "If the user's question is not clear and specific, resulting in the inability to call other tools, please call this tool to ask the user a rhetorical question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "description": "Rhetorical questions for users",
                            "type": "string"
                    }
                },
                "required": ["question"]
            }
        }
    }
)


tool_manager.register_tool(
    {
        "name":"give_final_response",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.lambda_give_final_response.give_final_response",
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
            }
        }
    }
)

tool_manager.register_tool(
    {
        "name":"search_lihoyo",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.lambda_retriever.retriever",
        "tool_def":{
                "name": "search_lihoyo",
                "description": "Retrieve knowledge about lihoyo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "description": "query to retrieve",
                            "type": "string"
                    }
                },
                "required": ["query"]
            }
        }
    }
)




    

         
