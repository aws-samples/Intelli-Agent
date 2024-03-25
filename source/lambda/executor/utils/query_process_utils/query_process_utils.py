from langchain import hub
import re
from ..llm_utils import Model as LLM_Model
from ..llm_utils import LLMChain
from langchain.schema.runnable import RunnableLambda,RunnablePassthrough
# from .prompt_template import get_conversation_query_rewrite_prompt as hyde_web_search_template
from ..langchain_utils import chain_logger
from .preprocess_utils import is_api_query, language_check,query_translate,get_service_name
# from langchain.memory import ConversationSummaryMemory, ChatMessageHistory
from ..constant import CONVERSATION_SUMMARY_TYPE,STEPBACK_PROMPTING_TYPE,HYDE_TYPE,QUERY_REWRITE_TYPE

# def query_rewrite_postprocess(r):
#     ret = re.findall('<questions>.*?</questions>',r,re.S)[0] 
#     questions  = re.findall('- (.*?)\n',ret,re.S)
#     return questions

# def get_query_rewrite_chain(
#         model_id,
#         model_kwargs=None,
#         query_expansion_template="hwchase17/multi-query-retriever",
#         query_key='query'
#     ):
#     query_expansion_template = hub.pull(query_expansion_template)
#     llm = LLM_Model.get_model(model_id=model_id, model_kwargs=model_kwargs)
#     chain = RunnableLambda(lambda x: query_expansion_template.invoke({"question": x[query_key]})) | llm | RunnableLambda(query_rewrite_postprocess)
#     return chain

def get_conversation_query_rewrite_chain(
        chat_history:list,
        conversation_query_rewrite_config
        ):
    # single turn
    if not chat_history:
        return RunnableLambda(lambda x:x['query'])
    cqr_chain = LLMChain.get_chain(
        intent_type=CONVERSATION_SUMMARY_TYPE,
        **conversation_query_rewrite_config
    )
    return cqr_chain


# def get_hyde_chain(
#     model_id,
#     model_kwargs=None,
#     query_key='query'
#     ):
#     llm = LLM_Model.get_model(
#         model_id=model_id,
#           model_kwargs=model_kwargs,
#           return_chat_model=False
#           )
#     chain = RunnablePassthrough.assign(
#         hyde_doc = RunnableLambda(lambda x: hyde_web_search_template.invoke({"query": x[query_key]})) | llm
#     )
#     return chain
    
def get_query_process_chain(
        chat_history,
        query_process_config,
        message_id=None
        ):
    query_rewrite_config = query_process_config['query_rewrite_config']
    conversation_query_rewrite_config = query_process_config['conversation_query_rewrite_config']
    hyde_config = query_process_config['hyde_config']
    translate_config = query_process_config['translate_config']

    query_rewrite_chain = RunnablePassthrough.assign(
        query_rewrite = LLMChain.get_chain(
        query_key='query',
        intent_type=QUERY_REWRITE_TYPE,
        **query_rewrite_config
    ))
    query_rewrite_chain = chain_logger(
        query_rewrite_chain,
        'query rewrite module',
        log_output_template='query_rewrite result: {query_rewrite}.',
        message_id=message_id
        )
    
    conversation_query_rewrite_chain = RunnablePassthrough.assign(
        conversation_query_rewrite=get_conversation_query_rewrite_chain(
            chat_history,
            conversation_query_rewrite_config=conversation_query_rewrite_config
            # llm_model_id = conversation_query_rewrite_config['model_id'],
            # model_kwargs = conversation_query_rewrite_config['model_kwargs']
        ))

    conversation_query_rewrite_chain = chain_logger(
        conversation_query_rewrite_chain,
        "conversation query rewrite module",
        log_output_template='conversation_query_rewrite result: {conversation_query_rewrite}.',
        message_id=message_id
    )

    preprocess_chain = RunnablePassthrough.assign(
          query_lang = RunnableLambda(lambda x:language_check(x['query'])),  
      ) | RunnablePassthrough.assign(
          translated_text = RunnableLambda(
              lambda x: query_translate(
                  x['query'],
                  lang=x['query_lang'],
                  translate_config=translate_config
                  ))
      )

    preprocess_chain = chain_logger(
        preprocess_chain,
        'preprocess module',
        log_output_template='\nquery lang:{query_lang},\nquery translated: {translated_text}',
        message_id=message_id
    )

    hyde_chain = RunnablePassthrough.assign(
        hyde_doc = LLMChain.get_chain(
            intent_type=HYDE_TYPE,
            query_key='query',
            **hyde_config
        )
        )

    hyde_chain = chain_logger(
        hyde_chain,
        "hyde chain",
        log_output_template="\nhyde generate passage: {hyde_doc}",
        message_id=message_id
    )

    stepback_promping_chain = RunnablePassthrough.assign(
        stepback_query = LLMChain.get_chain(
        intent_type=STEPBACK_PROMPTING_TYPE,
        **query_process_config['stepback_config']
        )
    )

    stepback_promping_chain = chain_logger(
        stepback_promping_chain,
        "stepback promping chain",
        log_output_template="stepback_promping_chain query: {stepback_query}",
        message_id=message_id
    )

    # 
    query_process_chain = preprocess_chain
    query_process_chain = conversation_query_rewrite_chain | preprocess_chain #  | stepback_promping_chain
      

    query_process_chain = chain_logger(
        query_process_chain,
        "query process module",
        message_id=message_id
   )
    
    return query_process_chain



