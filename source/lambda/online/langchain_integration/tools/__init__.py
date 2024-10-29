# from langchain.tools.base import StructuredTool,BaseTool,tool
# StructuredTool.from_function
# from langchain_experimental.tools import PythonREPLTool
# from langchain_core.utils.function_calling import convert_to_openai_function
# from llama_index.core.tools import FunctionTool
# from langchain.tools import BaseTool
# from pydantic import create_model

# from langchain_community.tools import WikipediaQueryRun


# builder = StateGraph(State)


# # Define nodes: these do the work
# builder.add_node("assistant", Assistant(part_1_assistant_runnable))
# builder.add_node("tools", create_tool_node_with_fallback(part_1_tools))
# # Define edges: these determine how the control flow moves
# builder.add_edge(START, "assistant")
# builder.add_conditional_edges(
#     "assistant",
#     tools_condition,
# )
# builder.add_edge("tools", "assistant")

# # The checkpointer lets the graph persist its state
# # this is a complete memory for the entire graph.
# memory = MemorySaver()
# part_1_graph = builder.compile(checkpointer=memory)

from typing import Optional,Union
from pydantic import BaseModel
import platform
import json 
import inspect 
from functools import wraps
import types 

from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from langchain.tools.base import StructuredTool as _StructuredTool ,BaseTool
from langchain_core.pydantic_v1 import create_model,BaseModel
from common_logic.common_utils.constant import SceneType
from common_logic.common_utils.lambda_invoke_utils import invoke_with_lambda
from functools import partial



class StructuredTool(_StructuredTool):
    pass_state:bool = False # if pass state into tool invoke 
    pass_state_name:str = "state" # pass state name 
    


class ToolIdentifier(BaseModel):
    scene: SceneType
    name: str
    
    @property
    def tool_id(self):
        return f"{self.scene}__{self.name}"


class ToolManager:
    tool_map = {}

    @staticmethod
    def convert_tool_def_to_pydantic(tool_id,tool_def:Union[dict,BaseModel]):
        if not isinstance(tool_def,dict):
            return tool_def 
        # convert tool definition to pydantic model 
        current_python_version = ".".join(platform.python_version().split(".")[:-1])
        data_model_types = get_data_model_types(
            DataModelType.PydanticBaseModel,
            target_python_version=PythonVersion(current_python_version)
        )
        parser = JsonSchemaParser(
            json.dumps(tool_def,ensure_ascii=False,indent=2),
            data_model_type=data_model_types.data_model,
            data_model_root_type=data_model_types.root_model,
            data_model_field_type=data_model_types.field_model,
            data_type_manager_type=data_model_types.data_type_manager,
            dump_resolve_reference_action=data_model_types.dump_resolve_reference_action,
            use_schema_description=True
        )
        result = parser.parse()
        new_tool_module = types.ModuleType(tool_id)
        exec(result, new_tool_module.__dict__)
        return new_tool_module.Model

    
    @staticmethod
    def get_tool_identifier(scene=None,name=None,tool_identifier=None):
        if tool_identifier is None:
            tool_identifier = ToolIdentifier(scene=scene,name=name)
        return tool_identifier


    @classmethod
    def register_lc_tool(
        cls,
        tool:BaseTool,
        scene=None,
        name=None,
        tool_identifier=None,
    ):
        tool_identifier = cls.get_tool_identifier(
            scene=scene,
            name=name,
            tool_identifier=None
        )
        assert isinstance(tool,BaseTool),(tool,type(tool))
        cls.tool_map[tool_identifier.tool_id] = tool 
        return tool
    

    @classmethod
    def register_func_as_tool(
        cls,
        func:callable,
        tool_def:dict,
        return_direct:False,
        scene=None,
        name=None,
        tool_identifier=None,
    ):
        tool_identifier = cls.get_tool_identifier(
            scene=scene,
            name=name,
            tool_identifier=tool_identifier
        )
        tool = StructuredTool.from_function(
            func=func,
            name=tool_identifier.name,
            args_schema=ToolManager.convert_tool_def_to_pydantic(
                tool_id=tool_identifier.tool_id,
                tool_def=tool_def
            ),
            return_direct=return_direct
        )
        # register tool 
        return ToolManager.register_lc_tool(
            tool_identifier=tool_identifier,
            tool=tool
        )
    

    @classmethod
    def register_aws_lambda_as_tool(
        cls,
        lambda_name:str,
        tool_def:dict,
        scene=None,
        name=None,
        tool_identifier=None,    
        return_direct=False                     
        ):

        def _func(**kargs):
            return invoke_with_lambda(lambda_name,kargs)

        tool_identifier = cls.get_tool_identifier(
            scene=scene,
            name=name,
            tool_identifier=tool_identifier
        )
        tool = StructuredTool.from_function(
            func=_func,
            name=tool_identifier.name,
            args_schema=ToolManager.convert_tool_def_to_pydantic(
                tool_id=tool_identifier.tool_id,
                tool_def=tool_def
            ),
            return_direct=return_direct
        )
        return ToolManager.register_lc_tool(
            tool_identifier=tool_identifier,
            tool=tool
        )

    @classmethod
    def register_common_rag_tool(
        cls,
        retriever_config:dict,
        description:str,
        scene=None,
        name=None,
        tool_identifier=None,   
        return_direct=False,
        pass_state=True,
        pass_state_name='state'
    ):
        assert scene == SceneType.COMMON, scene
        from .common_tools.rag import rag_tool

        tool_identifier = cls.get_tool_identifier(
            scene=scene,
            name=name,
            tool_identifier=tool_identifier
        )

        class RagModel(BaseModel):
            class Config:
                schema_extra = {"description": description}

        tool = StructuredTool.from_function(
            func=partial(rag_tool,
                         retriever_config=retriever_config
                        ),
            name=tool_identifier.name,
            args_schema=ToolManager.convert_tool_def_to_pydantic(
                tool_id=tool_identifier.tool_id,
                tool_def=RagModel
            ),
            description=description,
            return_direct=return_direct,
            pass_state=pass_state,
            pass_state_name=pass_state_name
        )
        
        return ToolManager.register_lc_tool(
            tool_identifier=tool_identifier,
            tool=tool
        )
        

    @classmethod
    def get_tool(cls, scene, name,**kwargs):
        # dynamic import 
        tool_identifier = ToolIdentifier(scene=scene, name=name)
        tool_id = tool_identifier.tool_id
        if tool_id not in cls.tool_map:
            TOOL_MOFULE_LOAD_FN_MAP[tool_id](**kwargs)
        return cls.tool_map[tool_id]


TOOL_MOFULE_LOAD_FN_MAP = {}


def lazy_tool_load_decorator(scene:SceneType,name):
    def decorator(func):
        tool_identifier = ToolIdentifier(scene=scene, name=name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "tool_identifier" in inspect.signature(func).parameters:
                kwargs = {**kwargs,"tool_identifier":tool_identifier}
            return func(*args, **kwargs)
        TOOL_MOFULE_LOAD_FN_MAP[tool_identifier.tool_id] = func
        return wrapper
    return decorator


############################# tool load func ######################


@lazy_tool_load_decorator(SceneType.COMMON,"get_weather")
def _load_common_weather_tool(tool_identifier:ToolIdentifier):
    from .common_tools import get_weather
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
        tool_identifier.scene,
        tool_identifier.name,
        get_weather.get_weather,
        tool_def,
        return_direct=False
    )


@lazy_tool_load_decorator(SceneType.COMMON,"give_rhetorical_question")
def _load_common_rhetorical_tool(tool_identifier:ToolIdentifier):
    from .common_tools import give_rhetorical_question
    tool_def = {
        "description": "If the user's question is not clear and specific, resulting in the inability to call other tools, please call this tool to ask the user a rhetorical question",
        "properties": {
            "question": {
                "description": "The rhetorical question to user",
                "type": "string"
            },
        }
    } 
    ToolManager.register_func_as_tool(
        tool_identifier.scene,
        tool_identifier.name,
        give_rhetorical_question.give_rhetorical_question,
        tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON,"give_final_response")
def _load_common_final_response_tool(tool_identifier:ToolIdentifier):
    from .common_tools import give_final_response
    
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
        tool_identifier.scene,
        tool_identifier.name,
        give_final_response.give_final_response,
        tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON,"chat")
def _load_common_chat_tool(tool_identifier:ToolIdentifier):
    from .common_tools import chat
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
        tool_identifier.scene,
        tool_identifier.name,
        chat.chat,
        tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON,"rag_tool")
def _load_common_rag_tool(tool_identifier:ToolIdentifier):
    from .common_tools import rag
    tool_def = {
        "description": "private knowledge",
        "properties": {
            "query": {
                "description": "query for retrieve",
                "type": "string"
                }
        },
        "required": ["query"]
    }
    ToolManager.register_func_as_tool(
        tool_identifier.scene,
        tool_identifier.name,
        rag.rag_tool,
        tool_def,
        return_direct=True
    )







    








