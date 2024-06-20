# tool calling chain
import json
from typing import List,Dict,Any
import re
from datetime import datetime 

from langchain.schema.runnable import (
    RunnableLambda,
)

from langchain_core.messages import(
    AIMessage,
    SystemMessage
) 
from langchain.prompts import ChatPromptTemplate

from langchain_core.messages import AIMessage,SystemMessage,HumanMessage

from common_utils.constant import (
    LLMTaskType,
    LLMModelType
)

from ..llm_chain_base import LLMChain
from ...llm_models import Model
from ..chat_chain import GLM4Chat9BChatChain

GLM4_SYSTEM_PROMPT = """你是安踏的客服助理小安, 主要职责是处理用户售前和售后的问题。{date_prompt}
请遵守下面的规范回答用户的问题。
## 回答规范
- 如果用户的提供的信息不足以回答问题，尽量反问用户。
- 回答简洁明了，一句话以内。

下面是当前用户正在浏览的商品信息:


## 商品信息
{goods_info}
"""



class GLM4Chat9BRetailToolCallingChain(GLM4Chat9BChatChain):
    model_id = LLMModelType.GLM_4_9B_CHAT
    intent_type = LLMTaskType.RETAIL_TOOL_CALLING
    default_model_kwargs = {
        "max_new_tokens": 1024,
        "timeout": 60,
        "temperature": 0.1,
    }
    DATE_PROMPT = "当前日期: %Y-%m-%d"
    
    @staticmethod
    def convert_openai_function_to_glm(tools:list[dict]):
        glm_tools = []
        for tool_def in tools:
            tool_name = tool_def['name']
            description = tool_def['description']
            params = []
            required = tool_def['parameters'].get("required",[])
            for param_name,param in tool_def['parameters'].get('properties',{}).items():
                params.append({
                    "name": param_name,
                    "description": param["description"],
                    "type": param["type"],
                    "required": param_name in required,             
                })  
            glm_tools.append({
                "name": tool_name,
                "description": description,
                "params": params
            })
        return glm_tools

    @staticmethod
    def format_fewshot_examples(fewshot_examples:list[dict]):
        fewshot_example_strs = []
        for i,example in enumerate(fewshot_examples):
            query = example['query']
            name = example['name']
            kwargs = example['kwargs']
            fewshot_example_str = f"## 示例{i+1}\n### 输入:\n{query}\n### 调用工具:\n{name}"
            fewshot_example_strs.append(fewshot_example_str)
        return "\n\n".join(fewshot_example_strs)


    @classmethod
    def create_system_prompt(cls,goods_info:str,tools:list,fewshot_examples:list) -> str:
        value = GLM4_SYSTEM_PROMPT.format(
            goods_info=goods_info,
            date_prompt=datetime.now().strftime(cls.DATE_PROMPT)
        )
        if tools:
            value += "\n\n# 可用工具"
        contents = []
        for tool in tools:
            content = f"\n\n## {tool['name']}\n\n{json.dumps(tool, ensure_ascii=False,indent=4)}"
            content += "\n在调用上述函数时，请使用 Json 格式表示调用的参数。"
            contents.append(content)
        value += "".join(contents)

        if not fewshot_examples:
            return value
        # add fewshot_exampls
        value += "\n\n# 下面给出不同问题调用不同工具的例子。"
        value += f"\n\n{cls.format_fewshot_examples(fewshot_examples)}"
        value += "\n\n请参考上述例子进行工具调用。"
        return value

    @classmethod
    def create_chat_history(cls,x,system_prompt=None):
        _chat_history = x['chat_history'] + \
            [{"role": "user","content": x['query']}] + \
            x['agent_chat_history']
        
        chat_history = []
        for message in _chat_history:
            new_message = message 
            if message['role'] == "ai":
                new_message = {
                    "role": "assistant",
                    "content": message['content']
                }
                tool_calls = message.get('additional_kwargs',{}).get("tool_calls",[])
                if tool_calls:
                    new_message['metadata'] = tool_calls[0]['name']
            chat_history.append(new_message)
        chat_history = [{"role": "system", "content": system_prompt}] + chat_history
        return chat_history

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        tools:list = kwargs.get('tools',[])
        fewshot_examples = kwargs.get('fewshot_examples',[])
        glm_tools = cls.convert_openai_function_to_glm(tools)
        system_prompt = cls.create_system_prompt(
            goods_info=kwargs['goods_info'], 
            tools=glm_tools,
            fewshot_examples=fewshot_examples
            )
        kwargs['system_prompt'] = system_prompt
        return super().create_chain(model_kwargs=model_kwargs,**kwargs)