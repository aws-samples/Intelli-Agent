import math 
from langchain.schema.messages import (
    HumanMessage,AIMessage,SystemMessage
)

from ..llm_utils import LLMChain
from ..constant import MKT_CONVERSATION_SUMMARY_TYPE

from ..ddb_utils import DynamoDBChatMessageHistory,filter_chat_history_by_time


def market_conversation_summary_entry(
        messages:list[dict],
        rag_config=None,
        stream=False
    ):

    if not rag_config['chat_history']:
        assert messages,messages
        chat_history = []
        for message in messages:
            role = message['role']
            content = message['content']
            assert role in ['user','ai']
            if role == 'user':
                chat_history.append(HumanMessage(content=content))
            else:
                chat_history.append(AIMessage(content=content))
        rag_config['chat_history'] = chat_history
    
    else:
        # filter by the window time
        time_window = rag_config.get('time_window',{})
        start_time = time_window.get('start_time',-math.inf)
        end_time = time_window.get('end_time',math.inf)
        assert isinstance(start_time, float) and isinstance(end_time, float), (start_time, end_time)
        chat_history = rag_config['chat_history']
        chat_history = filter_chat_history_by_time(chat_history,start_time=start_time,end_time=end_time)
        rag_config['chat_history'] = chat_history
    # rag_config['intent_config']['intent_type'] = IntentType.CHAT.value
    
    # query_input = """请简要总结上述对话中的内容,每一个对话单独一个总结，并用 '- '开头。 每一个总结要先说明问题。\n"""
    mkt_conversation_summary_config = rag_config["mkt_conversation_summary_config"]
    llm_chain = LLMChain.get_chain(
        intent_type=MKT_CONVERSATION_SUMMARY_TYPE,
        stream=stream,
        **mkt_conversation_summary_config, 
    )
    response = llm_chain.invoke({
        "chat_history": rag_config['chat_history'],
    })
    return response, [], {}, {}