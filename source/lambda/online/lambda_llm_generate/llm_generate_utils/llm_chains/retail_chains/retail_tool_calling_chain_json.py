# tool calling chain
import json
from typing import List,Dict,Any
import re
from datetime import datetime 
import copy

from langchain.schema.runnable import (
    RunnableLambda,
)

from langchain_core.messages import(
    AIMessage,
    SystemMessage
) 
from langchain.prompts import ChatPromptTemplate

from langchain_core.messages import AIMessage,SystemMessage,HumanMessage

from common_logic.common_utils.constant import (
    LLMTaskType,
    LLMModelType,
    MessageType
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
            [{"role":MessageType.HUMAN_MESSAGE_TYPE,"content": x['query']}] + \
            x['agent_chat_history']
        
        chat_history = []
        for message in _chat_history:
            new_message = message 
            if message['role'] == MessageType.AI_MESSAGE_TYPE:
                new_message = {
                    **message
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


from ..chat_chain import Qwen2Instruct7BChatChain



class Qwen2Instruct7BRetailToolCallingChain(Qwen2Instruct7BChatChain):
    model_id = LLMModelType.QWEN2INSTRUCT7B
    intent_type = LLMTaskType.RETAIL_TOOL_CALLING 
    default_model_kwargs = {
        "max_tokens": 1024,
        "temperature": 0.1,
    }

    DATE_PROMPT = "当前日期: %Y-%m-%d"
    FN_NAME = '✿FUNCTION✿'
    FN_ARGS = '✿ARGS✿'
    FN_RESULT = '✿RESULT✿'
    FN_EXIT = '✿RETURN✿'
    FN_STOP_WORDS = [FN_RESULT, f'{FN_RESULT}:', f'{FN_RESULT}:\n']

    FN_CALL_TEMPLATE_INFO_ZH="""# 工具

## 你拥有如下工具：

{tool_descs}"""


    FN_CALL_TEMPLATE_FMT_ZH="""## 你可以在回复中插入零次或者一次以下命令以调用工具：

%s: 工具名称，必须是[{tool_names}]之一。
%s: 工具输入
%s: 工具结果
%s: 根据工具结果进行回复""" % (
    FN_NAME,
    FN_ARGS,
    FN_RESULT,
    FN_EXIT,
)
    TOOL_DESC_TEMPLATE="""### {name_for_human}\n\n{name_for_model}: {description_for_model} 输入参数：{parameters} {args_format}"""
    
    FN_CALL_TEMPLATE=FN_CALL_TEMPLATE_INFO_ZH + '\n\n' + FN_CALL_TEMPLATE_FMT_ZH

    SYSTEM_PROMPT="""你是安踏的客服助理小安, 主要职责是处理用户售前和售后的问题。当前日期: 2024-06-18
请遵守下面的规范回答用户的问题。
## 回答规范
   - 如果用户的提供的信息不足以回答问题，尽量反问用户。
   - 回答简洁明了，一句话以内。

下面是当前用户正在浏览的商品信息:

## 当前用户正在浏览的商品信息
{goods_info}

{tools}
{fewshot_examples}
如果你发现工具的相关参数用户没有提供，请调用 `give_rhetorical_question` 工具反问用户。

你的每次回答都要按照下面的步骤输出你的思考, 并将思考过程写在xml 标签<thinking> 和 </thinking> 中:
    step 1. 判断是否需要使用某个工具。
    step 2. 基于当前上下文检查需要调用的工具对应的参数是否充足。如果不需要使用任何工具，请直接输出回答。"""
    @classmethod
    def get_function_description(cls,tool:dict):
        tool_name = tool['name']
        description = tool['description']
        params_str = json.dumps(tool.get('parameters',{}),ensure_ascii=False)
        args_format = '此工具的输入应为JSON对象。'
        return cls.TOOL_DESC_TEMPLATE.format(
            name_for_human=tool_name,
            name_for_model=tool_name,
            description_for_model=description,
            parameters=params_str,
            args_format=args_format
        ).rstrip()


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
    def create_system_prompt(cls,goods_info:str,tools:list[dict],fewshot_examples:list) -> str:
        tool_descs = '\n\n'.join(cls.get_function_description(tool) for tool in tools)
        tool_names = ','.join(tool['name'] for tool in tools)
        tool_system = cls.FN_CALL_TEMPLATE.format(
            tool_descs=tool_descs,
            tool_names=tool_names
            
        )
        fewshot_examples_str = ""
        if fewshot_examples:
            fewshot_examples_str = "\n\n# 下面给出不同问题调用不同工具的例子。"
            fewshot_examples_str += f"\n\n{cls.format_fewshot_examples(fewshot_examples)}"
            fewshot_examples_str += "\n\n请参考上述例子进行工具调用。"
            
        return cls.SYSTEM_PROMPT.format(
                goods_info=goods_info,
                tools=tool_system,
                fewshot_examples=fewshot_examples_str
            )

    @classmethod
    def create_chat_history(cls,x,system_prompt=None):
        # deal with function
        _chat_history = x['chat_history'] + \
            [{"role": MessageType.HUMAN_MESSAGE_TYPE,"content": x['query']}] + \
            x['agent_chat_history']
        
        # print(f'chat_history_before create: {_chat_history}')
        # merge chat_history
        chat_history = []
        if system_prompt is not None:
            chat_history.append({
                "role": MessageType.SYSTEM_MESSAGE_TYPE,
                "content":system_prompt
            })
        
        # move tool call results  to assistant
        for i,message in enumerate(copy.deepcopy(_chat_history)):
            role = message['role']
            if i==0:
                assert role == MessageType.HUMAN_MESSAGE_TYPE, f"The first message should comes from human role"
            
            if role == MessageType.TOOL_MESSAGE_TYPE:
                assert chat_history[-1]['role'] == MessageType.AI_MESSAGE_TYPE,_chat_history
                chat_history[-1]['content'] += message['content']
                continue 
            elif role == MessageType.AI_MESSAGE_TYPE:
                # continue ai message
                if chat_history[-1]['role'] == MessageType.AI_MESSAGE_TYPE:
                    chat_history[-1]['content'] += message['content']
                    continue

            chat_history.append(message)
        
        # move the last tool call message to user 
        if chat_history[-1]['role'] == MessageType.AI_MESSAGE_TYPE:
            assert chat_history[-2]['role'] == MessageType.HUMAN_MESSAGE_TYPE,chat_history
            tool_calls = chat_history[-1].get("additional_kwargs",{}).get("tool_calls",[])
            if tool_calls:
                chat_history[-2]['content'] += ("\n\n" + chat_history[-1]['content'])
                chat_history = chat_history[:-1]

        return chat_history

    
    @classmethod
    def parse_function_calls_from_ai_message(cls,message:dict):
        stop_reason = message['stop_reason']
        content =  "<thinking>" + message['text']
        stop_reason = stop_reason or ""
        function_calls = re.findall(f"{cls.FN_NAME}.*?{cls.FN_RESULT}", content + stop_reason,re.S)
        return {
            "function_calls":function_calls,
            "content":content
        }
    
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        tools:list = kwargs.get('tools',[])
        fewshot_examples = kwargs.get('fewshot_examples',[])
        system_prompt = cls.create_system_prompt(
            goods_info=kwargs['goods_info'], 
            tools=tools,
            fewshot_examples=fewshot_examples
            )
        model_kwargs = model_kwargs or {}
        kwargs['system_prompt'] = system_prompt
        model_kwargs = {**model_kwargs}
        model_kwargs["stop"] = ['✿RESULT✿', '✿RESULT✿:', '✿RESULT✿:\n']
        model_kwargs["prefill"] = "我先看看调用哪个工具，下面是我的思考过程:\n<thinking>\nstep 1."
        return super().create_chain(model_kwargs=model_kwargs,**kwargs)
        


class Qwen2Instruct72BRetailToolCallingChain(Qwen2Instruct7BRetailToolCallingChain):
    model_id = LLMModelType.QWEN2INSTRUCT72B

