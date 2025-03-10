from typing import Optional, Union
from pydantic import BaseModel
import platform
import json
import inspect
from functools import wraps
import types

from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.format import DatetimeClassType
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
from langchain.tools.base import StructuredTool as _StructuredTool, BaseTool
from shared.constant import SceneType
from common_logic.common_utils.lambda_invoke_utils import invoke_with_lambda
from functools import partial


class StructuredTool(_StructuredTool):
    pass


class ToolIdentifier(BaseModel):
    scene: SceneType
    name: str

    @property
    def tool_id(self):
        return f"{self.scene}__{self.name}"


class ToolManager:
    tool_map = {}

    @staticmethod
    def convert_tool_def_to_pydantic(tool_id, tool_def: Union[dict, BaseModel]):
        if not isinstance(tool_def, dict):
            return tool_def
        # convert tool definition to pydantic model
        current_python_version = ".".join(
            platform.python_version().split(".")[:-1])
        data_model_types = get_data_model_types(
            DataModelType.PydanticBaseModel,
            target_python_version=PythonVersion(current_python_version),
            target_datetime_class=DatetimeClassType.Datetime
        )
        parser = JsonSchemaParser(
            json.dumps(tool_def, ensure_ascii=False, indent=2),
            data_model_type=data_model_types.data_model,
            data_model_root_type=data_model_types.root_model,
            data_model_field_type=data_model_types.field_model,
            data_type_manager_type=data_model_types.data_type_manager,
            dump_resolve_reference_action=data_model_types.dump_resolve_reference_action,
            use_schema_description=True
        )
        result = parser.parse()
        result = result.replace("from __future__ import annotations", "")
        new_tool_module = types.ModuleType(tool_id)
        exec(result, new_tool_module.__dict__)
        model_cls = new_tool_module.Model
        return model_cls

    @staticmethod
    def get_tool_identifier(scene=None, name=None, tool_identifier=None):
        if tool_identifier is None:
            tool_identifier = ToolIdentifier(scene=scene, name=name)
        return tool_identifier

    @classmethod
    def register_lc_tool(
        cls,
        tool: BaseTool,
        scene=None,
        name=None,
        tool_identifier=None,
    ):
        tool_identifier = cls.get_tool_identifier(
            scene=scene,
            name=name,
            tool_identifier=tool_identifier
        )
        assert isinstance(tool, BaseTool), (tool, type(tool))
        cls.tool_map[tool_identifier.tool_id] = tool
        return tool

    @classmethod
    def register_func_as_tool(
        cls,
        func: callable,
        tool_def: dict,
        return_direct: False,
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
        lambda_name: str,
        tool_def: dict,
        scene=None,
        name=None,
        tool_identifier=None,
        return_direct=False
    ):

        def _func(**kargs):
            return invoke_with_lambda(lambda_name, kargs)

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
        retriever_config: dict,
        description: str,
        scene=None,
        name=None,
        tool_identifier=None,
        return_direct=False
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
            response_format="content_and_artifact"
        )

        return ToolManager.register_lc_tool(
            tool_identifier=tool_identifier,
            tool=tool
        )

    @classmethod
    def get_tool(cls, scene, name, **kwargs):
        # dynamic import
        tool_identifier = ToolIdentifier(scene=scene, name=name)
        tool_id = tool_identifier.tool_id
        if tool_id not in cls.tool_map:
            TOOL_MOFULE_LOAD_FN_MAP[tool_id](**kwargs)
        return cls.tool_map[tool_id]


TOOL_MOFULE_LOAD_FN_MAP = {}


def lazy_tool_load_decorator(scene: SceneType, name):
    def decorator(func):
        tool_identifier = ToolIdentifier(scene=scene, name=name)

        @wraps(func)
        def wrapper(*args, **kwargs):
            if "tool_identifier" in inspect.signature(func).parameters:
                kwargs = {**kwargs, "tool_identifier": tool_identifier}
            return func(*args, **kwargs)
        TOOL_MOFULE_LOAD_FN_MAP[tool_identifier.tool_id] = wrapper
        return wrapper
    return decorator

from . import common_tools
