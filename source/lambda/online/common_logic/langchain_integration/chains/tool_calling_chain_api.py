# tool calling chain
import json
from typing import List,Dict,Any
from collections import defaultdict

from common_logic.common_utils.prompt_utils import get_prompt_template
from langchain_core.messages import(
    AIMessage,
    SystemMessage
) 
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage,SystemMessage
from langchain.tools.base import BaseTool
from langchain_core.language_models import BaseChatModel

from common_logic.common_utils.constant import (
    LLMTaskType,
    LLMModelType,
    MessageType
)
from common_logic.common_utils.time_utils import get_china_now

from . import LLMChain
from ..chat_models import Model


class Claude2ToolCallingChain(LLMChain):
    model_id = LLMModelType.CLAUDE_2
    intent_type = LLMTaskType.TOOL_CALLING_API
    default_model_kwargs = {
        "max_tokens": 2000,
        "temperature": 0.1,
        "top_p": 0.9
    }

    @classmethod
    def create_chat_history(cls,x):
        chat_history = x['chat_history'] + \
            [{"role": MessageType.HUMAN_MESSAGE_TYPE,"content": x['query']}] + \
            x['agent_tool_history']
        return chat_history

    @classmethod
    def get_common_system_prompt(cls,system_prompt_template:str):
        now = get_china_now()
        date_str = now.strftime("%Y年%m月%d日")
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[now.weekday()]
        system_prompt = system_prompt_template.format(date=date_str,weekday=weekday)
        return system_prompt


    @classmethod
    def bind_tools(cls,llm:BaseChatModel,tools:List[BaseTool], fewshot_examples=None, fewshot_template=None,tool_choice='any'):
        tools = [tool.model_copy() for tool in tools]
        if not fewshot_examples:
            if getattr(llm,"enable_auto_tool_choice",True):
                return llm.bind_tools(tools,tool_choice=tool_choice)
            return llm.bind_tools(tools)

        # add fewshot examples to tool description
        tools_map = {tool.name:tool for tool in tools}

        # group fewshot examples
        fewshot_examples_grouped = defaultdict(list)
        for example in fewshot_examples:
            fewshot_examples_grouped[example['name']].append(example)

        for tool_name,examples in fewshot_examples_grouped.items():
            tool = tools_map[tool_name]
            tool.description += "\n\nHere are some examples where this tool are called:\n"
            examples_strs = []
            for example in examples:
                params_str = json.dumps(example['kwargs'],ensure_ascii=False)
                examples_strs.append(
                    fewshot_template.format(
                        query=example['query'],
                        args=params_str
                    )
                )
            
            tool.description += "\n\n".join(examples_strs)
        
        if getattr(llm,"enable_auto_tool_choice",True):
            return llm.bind_tools(tools,tool_choice=tool_choice)
        return llm.bind_tools(tools)
    
        
    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        tools:list = kwargs['tools']
        assert all(isinstance(tool,BaseTool) for tool in tools),tools
        fewshot_examples = kwargs.get('fewshot_examples',[])
        if fewshot_examples:
            fewshot_examples.append({
                "name": "give_rhetorical_question",
                "query": "今天天气怎么样?",
                "kwargs": {"question": "请问你想了解哪个城市的天气?"}
            })
        agent_system_prompt = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="agent_system_prompt"     
        ).prompt_template

        agent_system_prompt = kwargs.get("agent_system_prompt",None) or agent_system_prompt

        agent_system_prompt = cls.get_common_system_prompt(
            agent_system_prompt
        )
        
        # tool fewshot prompt 
        tool_fewshot_prompt = get_prompt_template(
            model_id=cls.model_id,
            task_type=cls.intent_type,
            prompt_name="tool_fewshot_prompt"
        ).prompt_template
        tool_fewshot_prompt = kwargs.get('tool_fewshot_prompt',None) or tool_fewshot_prompt

        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}

        llm = Model.get_model(
            model_id=cls.model_id,
            model_kwargs=model_kwargs,
        )

        llm = cls.bind_tools(llm,tools,fewshot_examples,fewshot_template=tool_fewshot_prompt)

        tool_calling_template = ChatPromptTemplate.from_messages(
            [
               SystemMessage(content=agent_system_prompt), 
               ("placeholder", "{chat_history}"),
               ("human", "{query}"),
               ("placeholder", "{agent_tool_history}"),

            ]
        )
        chain = tool_calling_template | llm 
        return chain


class Claude21ToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_21


class Claude3SonnetToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_SONNET


class Claude3HaikuToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude35SonnetToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_5_SONNET


class Claude35SonnetV2ToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_5_SONNET_V2


class Claude35HaikuToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.CLAUDE_3_5_HAIKU


class Llama31Instruct70BToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.LLAMA3_1_70B_INSTRUCT


class MistraLlarge2407ToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.MISTRAL_LARGE_2407


class CohereCommandRPlusToolCallingChain(Claude2ToolCallingChain):
    model_id = LLMModelType.COHERE_COMMAND_R_PLUS
