from ...constant import MKT_QUERY_REWRITE_TYPE
from ..llm_chains.chat_chain import Iternlm2Chat7BChatChain,Claude2ChatChain
import re
from ..llm_models import Model
from langchain.schema.runnable import RunnableLambda,RunnablePassthrough
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage



class Iternlm2Chat7BMKTQueryRewriteChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-7b"
    intent_type = MKT_QUERY_REWRITE_TYPE

    default_model_kwargs = {
        "temperature":0.1,
        "max_new_tokens": 200
    }

    @classmethod
    def create_prompt(cls,x):
        meta_instruction = """你是一个句子改写专家。你需要结合当前的历史对话消息将给定的句子按照下面的规则改写成方便检索的形式。
改写规则:
    - 修改之后应该为一个疑问句。
    - 你需要尽可能将当前句子放到”亚马逊云科技“ / ”Amazon AWS“的语境下进行改写。
    - 如果原句子本身比较完整就不需要进行改写。

下面有一些示例:
原句子: Amazon ec2
改写为: 什么是 Amazon EC2？

原句子: AWS 有上海区域吗？
改写为: AWS 有上海区域吗？
"""
        prompt = cls.build_prompt(
            query=f"原句子: {x['query']}",
            history=cls.create_history(x),
            meta_instruction=meta_instruction
        )  + "改写为:"
        return prompt


class Iternlm2Chat20BMKTQueryRewriteChain(Iternlm2Chat7BMKTQueryRewriteChain):
    model_id = "internlm2-chat-20b"
    intent_type = MKT_QUERY_REWRITE_TYPE


claude_system_message = """你是一个句子改写专家。你需要将给定的句子按照下面的规则改写成方便检索的形式。
改写规则:
    - 修改之后应该为一个疑问句。
    - 你需要尽可能将当前句子放到”亚马逊云科技“ / ”Amazon AWS“的语境下进行改写。
    - 如果原句子本身比较完整就不需要进行改写。

下面有一些示例:
原句子: Amazon ec2
改写为: 什么是 Amazon EC2？

原句子: AWS 有上海区域吗？
改写为: AWS 有上海区域吗？
"""

class Claude2MKTQueryRewriteChain(Claude2ChatChain):
    model_id = 'anthropic.claude-v2'
    intent_type = MKT_QUERY_REWRITE_TYPE

    default_model_kwargs = {
      "temperature": 0.1,
      "max_tokens": 100,
      "stop_sequences": [
        "\n\nHuman:"
      ]
    }

    @staticmethod
    def get_messages(x): 
       messages = [
           SystemMessage(content=claude_system_message),
           HumanMessage(content=f'原句子: {x["query"]}'),
           AIMessage(content="改写为:")
           ]
       return messages

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        stream = kwargs.get('stream',False)
        
        prompt = RunnableLambda(lambda x: cls.get_messages(x))
  
        llm = Model.get_model(
            cls.model_id,
            model_kwargs=model_kwargs,
            **kwargs
        )
        
        chain = prompt | llm | RunnableLambda(lambda x: x.content.strip())

        return chain 


class Claude21MKTQueryRewriteChain(Claude2MKTQueryRewriteChain):
    model_id = 'anthropic.claude-v2:1'

class ClaudeInstanceMKTQueryRewriteChain(Claude2MKTQueryRewriteChain):
    model_id = 'anthropic.claude-instant-v1'

class Claude3HaikuMKTQueryRewriteChain(Claude2MKTQueryRewriteChain):
    model_id =  "anthropic.claude-3-haiku-20240307-v1:0"

class Claude3SonnetMKTQueryRewriteChain(Claude2MKTQueryRewriteChain):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
