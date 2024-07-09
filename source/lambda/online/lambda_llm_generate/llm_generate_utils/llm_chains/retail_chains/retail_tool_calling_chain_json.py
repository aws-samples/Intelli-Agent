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
from functions import get_tool_by_name

from ..llm_chain_base import LLMChain
from ...llm_models import Model
from ..chat_chain import GLM4Chat9BChatChain
from common_logic.common_utils.logger_utils import get_logger

logger = get_logger("retail_tool_calling_chain_json")

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

    DATE_PROMPT = "当前日期: %Y-%m-%d 。"
    FN_NAME = '✿FUNCTION✿'
    FN_ARGS = '✿ARGS✿'
    FN_RESULT = '✿RESULT✿'
    FN_EXIT = '✿RETURN✿'
    FN_STOP_WORDS = [FN_RESULT, f'{FN_RESULT}:', f'{FN_RESULT}:\n']
    thinking_tag = "思考"
    fix_reply_tag = "固定回复"
    goods_info_tag = "商品信息"
    prefill_after_thinking = f"<{thinking_tag}>"
    prefill_after_second_thinking = ""
    prefill = prefill_after_thinking


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

#     SYSTEM_PROMPT=f"""你是安踏天猫的客服助理小安, 主要职责是处理用户售前和售后的问题。{{date_prompt}}

# {{tools}}
# {{fewshot_examples}}

# ## 当前用户正在浏览的商品信息
# {{goods_info}}

# # 思考
# 你每次给出最终回复前都要按照下面的步骤输出你的思考过程, 注意你并不需要每次都进行所有步骤的思考。并将思考过程写在 XML 标签 <{thinking_tag}> 和 </{thinking_tag}> 中:
#     Step 1. 根据各个工具的描述，分析当前用户的回复和各个示例中的Input相关性，如果跟某个示例对应的Input相关性强，直接跳过后续所有步骤，之后按照示例中Output的工具名称进行调用。
#     Step 2. 如果你觉得可以依据商品信息 <{goods_info_tag}> 里面的内容进行回答，就直接就回答，不需要调用任何工具。并结束思考。
#     Step 3. 如果你觉得当前用户的回复意图不清晰，或者仅仅是表达一些肯定的内容，或者和历史消息没有很强的相关性，同时当前不是第一轮对话，直接回复用户下面 XML 标签 <{fix_reply_tag}> 里面的内容:
#             <{fix_reply_tag}> 亲亲，请问还有什么问题吗？ </{fix_reply_tag}>
#     Step 4. 如果需要调用某个工具，检查该工具的必选参数是否可以在上下文中找到。结束思考，输出结束思考符号。

# ## 回答规范
#    - 如果客户没有明确指出在哪里购买的商品，则默认都是在天猫平台购买的
#    - 当前主要服务天猫平台的客户，如果客户询问其他平台的问题，直接回复 “不好意思，亲亲，这里是天猫店铺，只能为您解答天猫的问题。建议您联系其他平台的客服或售后人员给您提供相关的帮助和支持。谢谢！”
#    - 如果客户的回复里面包含订单号，则直接回复 ”您好，亲亲，这就帮您去查相关订单信息。请问还有什么问题吗？“
#    - 只能思考一次，在结束思考符号“</思考>”之后给出最终的回复。不要重复输出文本，段落，句子。思考之后的文本保持简洁，有且仅能包含一句话。{{non_ask_rules}}"""
#     SYSTEM_PROMPT=f"""你是安踏天猫的客服助理小安, 主要职责是处理用户售前和售后的问题。{{date_prompt}}

# {{tools}}
# {{fewshot_examples}}

# ## 当前用户正在浏览的商品信息
# {{goods_info}}

# # 你每次给出最终回复前都要参考下面的回复策略:
#     1. 根据各个工具的描述，分析当前用户的回复和各个示例中的Input相关性，如果跟某个示例对应的Input相关性强，直接跳过后续所有步骤，之后按照示例中Output的工具名称进行调用。
#     2. 如果你觉得可以依据商品信息 <{goods_info_tag}> 里面的内容进行回答，就直接就回答，不需要调用任何工具。
#     3. 如果你觉得当前用户的回复意图不清晰，或者仅仅是表达一些肯定的内容，或者和历史消息没有很强的相关性，同时当前不是第一轮对话，直接回复用户下面 XML 标签 <{fix_reply_tag}> 里面的内容:
#             <{fix_reply_tag}> 亲亲，请问还有什么问题吗？ </{fix_reply_tag}>
#     4. 如果需要调用某个工具，检查该工具的必选参数是否可以在上下文中找到。

# ## 回答规范
#    - 如果客户没有明确指出在哪里购买的商品，则默认都是在天猫平台购买的
#    - 当前主要服务天猫平台的客户，如果客户询问其他平台的问题，直接回复 “不好意思，亲亲，这里是天猫店铺，只能为您解答天猫的问题。建议您联系其他平台的客服或售后人员给您提供相关的帮助和支持。谢谢！“
#    - 如果客户的回复里面包含订单号，则直接回复 “您好，亲亲，这就帮您去查相关订单信息。请问还有什么问题吗？“{{non_ask_rules}}"""

    SYSTEM_PROMPT=f"""你是安踏天猫的客服助理小安, 主要职责是处理用户售前和售后的问题。{{date_prompt}}

{{tools}}
{{fewshot_examples}}

## 当前用户正在浏览的商品信息
{{goods_info}}

# 回复策略
在你给出最终回复前可以在XML标签 <{thinking_tag}> 和 </{thinking_tag}> 中输出你的回复策略。下面是一些常见的回复策略:
    - 如果根据各个工具的描述，当前用户的回复跟某个示例对应的Input相关性强，直接按照示例中Output的工具名称进行调用。
    - 考虑使用商品信息 <{goods_info_tag}> 里面的内容回答用户的问题。
    - 如果你觉得当前用户的回复意图不清晰，或者仅仅是表达一些肯定的内容，或者和历史消息没有很强的相关性，同时当前不是第一轮对话，直接回复用户: “ 亲亲，请问还有什么问题吗？“
    - 如果需要调用某个工具，检查该工具的必选参数是否可以在上下文中找到。
    - 如果客户的回复里面包含订单号，则直接回复 “您好，亲亲，这就帮您去查相关订单信息。请问还有什么问题吗？“
    - 当前主要服务天猫平台的客户，如果客户询问其他平台的问题，直接回复 “不好意思，亲亲，这里是天猫店铺，只能为您解答天猫的问题。建议您联系其他平台的客服或售后人员给您提供相关的帮助和支持。谢谢！“

## Tips
   - 如果客户没有明确指出在哪里购买的商品，则默认都是在天猫平台购买的。
   - 回答必须简洁，不允许出现超过2句话的回复。{{non_ask_rules}}"""
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


    @classmethod
    def format_fewshot_examples(cls,fewshot_examples:list[dict]):
        fewshot_example_strs = []
        for i,example in enumerate(fewshot_examples):
            query = example['query']
            name = example['name']
            kwargs = example['kwargs']
            fewshot_example_str = f"""## 工具调用例子{i+1}\nInput:\n{query}\nOutput:\n{cls.FN_NAME}: {name}\n{cls.FN_ARGS}: {json.dumps(kwargs,ensure_ascii=False)}\n{cls.FN_RESULT}"""
            fewshot_example_strs.append(fewshot_example_str)
        return "\n\n".join(fewshot_example_strs)
     
    
    @classmethod
    def create_system_prompt(cls,goods_info:str,tools:list[dict],fewshot_examples:list,create_time=None) -> str:
        tool_descs = '\n\n'.join(cls.get_function_description(tool) for tool in tools)
        tool_names = ','.join(tool['name'] for tool in tools)
        tool_system = cls.FN_CALL_TEMPLATE.format(
            tool_descs=tool_descs,
            tool_names=tool_names
        )
        fewshot_examples_str = ""
        if fewshot_examples:
            fewshot_examples_str = "\n\n# 下面给出不同客户回复下调用不同工具的例子。"
            fewshot_examples_str += f"\n\n{cls.format_fewshot_examples(fewshot_examples)}"
            fewshot_examples_str += "\n\n请参考上述例子进行工具调用。"
        
        non_ask_tool_list = []
        for tool in tools:
            should_ask_parameter = get_tool_by_name(tool['name']).should_ask_parameter
            if should_ask_parameter != "True":
                format_string = tool['name']+"工具"+should_ask_parameter
                non_ask_tool_list.append(format_string)
        if len(non_ask_tool_list) == 0:
            non_ask_rules = ""
        else:
            non_ask_rules = "\n - " + '，'.join(non_ask_tool_list)

        if create_time:
            datetime_object = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S.%f')
        else:
            datetime_object = datetime.now()
            logger.info(f"create_time: {create_time} is not valid, use current time instead.")
        
        return cls.SYSTEM_PROMPT.format(
                goods_info=goods_info,
                tools=tool_system,
                fewshot_examples=fewshot_examples_str,
                non_ask_rules=non_ask_rules,
                date_prompt=datetime_object.strftime(cls.DATE_PROMPT)
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
        content =  f"{cls.prefill}" + message['text']
        content = content.strip()
        stop_reason = stop_reason or ""
    

        function_calls = re.findall(f"{cls.FN_NAME}.*?{cls.FN_RESULT}", content + stop_reason,re.S)
        return {
            "function_calls":function_calls,
            "content":content
        }
    
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        tools:list = kwargs.get('tools',[])
        # add  extral tools
        if "give_rhetorical_question" not in tools:
            tools.append(get_tool_by_name("give_rhetorical_question").tool_def)
        fewshot_examples = kwargs.get('fewshot_examples',[])
        system_prompt = cls.create_system_prompt(
            goods_info=kwargs['goods_info'], 
            create_time=kwargs.get('create_time',None),
            tools=tools,
            fewshot_examples=fewshot_examples
            )

        current_agent_recursion_num = kwargs['current_agent_recursion_num']
        
        # give different prefill
        if current_agent_recursion_num == 0:
            cls.prefill = cls.prefill_after_thinking
        else:
            cls.prefill = cls.prefill_after_second_thinking
        # cls.prefill = ''

        model_kwargs = model_kwargs or {}
        kwargs['system_prompt'] = system_prompt
        model_kwargs = {**model_kwargs}
        # model_kwargs["stop"] = model_kwargs.get("stop",[]) + ['✿RESULT✿', '✿RESULT✿:', '✿RESULT✿:\n','✿RETURN✿',f'<{cls.thinking_tag}>',f'<{cls.thinking_tag}/>']
        model_kwargs["stop"] = model_kwargs.get("stop",[]) + ['✿RESULT✿', '✿RESULT✿:', '✿RESULT✿:\n','✿RETURN✿',f'<{cls.thinking_tag}/>']
        # model_kwargs["prefill"] = "我先看看调用哪个工具，下面是我的思考过程:\n<thinking>\nstep 1."
        model_kwargs["prefill"] = f'{cls.prefill}'
        return super().create_chain(model_kwargs=model_kwargs,**kwargs)
        

class Qwen2Instruct72BRetailToolCallingChain(Qwen2Instruct7BRetailToolCallingChain):
    model_id = LLMModelType.QWEN2INSTRUCT72B

