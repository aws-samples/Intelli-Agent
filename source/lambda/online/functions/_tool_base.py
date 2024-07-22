from typing import Union,Callable
from langchain.pydantic_v1 import BaseModel,Field
from enum import Enum
from common_logic.common_utils.constant import SceneType,ToolRuningMode

class ToolDefType(Enum):
    openai = "openai"


class Tool(BaseModel):
    name: str = Field(description="tool name")
    lambda_name: str = Field(description="lambda name")
    lambda_module_path: Union[str, Callable] = Field(description="local module path")
    handler_name:str = Field(description="local handler name", default="lambda_handler")
    tool_def: dict = Field(description="tool definition")
    tool_init_kwargs:dict = Field(description="tool initial kwargs",default=None)
    running_mode: str = Field(description="tool running mode, can be loop or output", default=ToolRuningMode.LOOP)
    tool_def_type: ToolDefType = Field(description="tool definition type",default=ToolDefType.openai.value)
    scene: str = Field(description="tool use scene",default=SceneType.COMMON)
    # should_ask_parameter: bool = Field(description="tool use scene")

class ToolManager:
    def __init__(self) -> None:
        self.tools = {}
    
    def get_tool_id(self,tool_name:str,scene:str):
        return f"{tool_name}__{scene}"
    
    def register_tool(self,tool_info:dict):
        tool_def = tool_info['tool_def']
        if "parameters" not in tool_def:
            tool_def['parameters'] = {
                "type": "object",
                "properties": {},
                "required": []
            }

        tool = Tool(**tool_info)
        assert tool.tool_def_type == ToolDefType.openai.value, f"tool_def_type: {tool.tool_def_type} not support"
        self.tools[self.get_tool_id(tool.name,tool.scene)] = tool

    def get_tool_by_name(self,name,scene=SceneType.COMMON):
        return self.tools[self.get_tool_id(name,scene)]

tool_manager = ToolManager()
get_tool_by_name = tool_manager.get_tool_by_name





