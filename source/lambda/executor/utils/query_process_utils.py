from langchain import hub
import re
from llm_utils import Model as LLM_Model
from langchain.schema.runnable import RunnableLambda,RunnablePassthrough
from prompt_template import get_conversation_query_rewrite_prompt,hyde_web_search_template
from langchain_utils import chain_logger
from preprocess_utils import is_api_query, language_check,query_translate,get_service_name

def query_rewrite_postprocess(r):
    ret = re.findall('<questions>.*?</questions>',r,re.S)[0] 
    questions  = re.findall('- (.*?)\n',ret,re.S)
    return questions

def get_query_rewrite_chain(
        llm_model_id,
        model_kwargs=None,
        query_expansion_template="hwchase17/multi-query-retriever",
        query_key='query'
    ):
    query_expansion_template = hub.pull(query_expansion_template)
    llm = LLM_Model.get_model(model_id=llm_model_id, model_kwargs=model_kwargs)
    chain = RunnableLambda(lambda x: query_expansion_template.invoke({"question": x[query_key]})) | llm | RunnableLambda(query_rewrite_postprocess)
    return chain

def get_conversation_query_rewrite_chain(
        chat_history:list,
        llm_model_id,
        model_kwargs=None
        ):
    # single turn
    if not chat_history:
        return RunnableLambda(lambda x:x['query'])
    cqr_prompt = get_conversation_query_rewrite_prompt(chat_history)
    llm = LLM_Model.get_model(
        model_id=llm_model_id,
          model_kwargs=model_kwargs,
          return_chat_model=True
          )
    cqr_chain = cqr_prompt | llm | RunnableLambda(lambda x:x.dict()['content'])
    return cqr_chain


def get_hyde_chain(
    llm_model_id,
    model_kwargs=None,
    query_key='query'
    ):
    llm = LLM_Model.get_model(
        model_id=llm_model_id,
          model_kwargs=model_kwargs,
          return_chat_model=False
          )
    chain = RunnablePassthrough.assign(
        hyde_doc = RunnableLambda(lambda x: hyde_web_search_template.invoke({"query": x[query_key]})) | llm
    )
    
    return chain
    
def get_query_process_chain(
        chat_history,
        query_rewrite_config,
        conversation_query_rewrite_config,
        hyde_config
        ):
    query_rewrite_chain = get_query_rewrite_chain(
        llm_model_id = query_rewrite_config['model_id'],
        model_kwargs = query_rewrite_config['model_kwargs'],
        query_key='conversation_query_rewrite'
    )
    query_rewrite_chain = chain_logger(
        query_rewrite_chain,
        'query rewrite module',
        log_output_template='query_rewrite result: {query_rewrite}.'
        )
    
    # conversation_query_rewrite_chain = RunnablePassthrough.assign(
    #     conversation_query_rewrite=get_conversation_query_rewrite_chain(
    #         chat_history,
    #         llm_model_id = conversation_query_rewrite_config['model_id'],
    #         model_kwargs = conversation_query_rewrite_config['model_kwargs']
    #     ))

    # conversation_query_rewrite_chain = chain_logger(
    #     conversation_query_rewrite_chain,
    #     "conversation query rewrite module",
    #     log_output_template='conversation_query_rewrite result: {conversation_query_rewrite}.'
    # )

    preprocess_chain = RunnablePassthrough.assign(
          query_lang = RunnableLambda(lambda x:language_check(x['query'])),  
      ) | RunnablePassthrough.assign(
          translated_text = RunnableLambda(lambda x: query_translate(x['query'],lang=x['query_lang'])),
      )

    preprocess_chain = chain_logger(
        preprocess_chain,
        'preprocess module',
        log_output_template='\nquery lang:{query_lang},\nquery translated: {translated_text}'
    )

    hyde_chain = get_hyde_chain(
        hyde_config['model_id'],
        hyde_config['model_kwargs']
    )

    hyde_chain = chain_logger(
        hyde_chain,
        "hyde chain",
        log_output_template="\nhyde generate passage: {hyde_doc}"
    )

    # 
    query_process_chain = preprocess_chain
    # query_process_chain = conversation_query_rewrite_chain | preprocess_chain 
      
    
    query_process_chain = chain_logger(
        query_process_chain,
        "query process module"
   )
    
    return query_process_chain



