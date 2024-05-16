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
                "description": "如果用户的提问不清晰，不具体，导致不能调用其他工具，请调用本工具对用户进行反问",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "description": "反问用户，让其将问题补全",
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
                "description": "如果其他工具都不需要去调用, 请调用当前工具完成对用户的直接回复",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "description": "对用户的回复",
                            "type": "string"
                    }
                },
                "required": ["response"]
            }
        }
    }
)




    

         
