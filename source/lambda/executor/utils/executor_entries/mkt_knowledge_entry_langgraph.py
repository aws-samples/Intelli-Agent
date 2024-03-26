import logging 
import json 
import os
import boto3
from functools import partial 
from textwrap import dedent
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.merger_retriever import MergerRetriever

from langgraph.graph import StateGraph, END
from typing import TypedDict, Any

from ..intent_utils import IntentRecognitionAOSIndex
from ..llm_utils import LLMChain
from ..serialization_utils import JSONEncoder
from ..langchain_utils import chain_logger,RunnableDictAssign,RunnableParallelAssign
from ..constant import IntentType, CONVERSATION_SUMMARY_TYPE, RerankerType
import asyncio

from ..retriever import (
    QueryDocumentKNNRetriever,
    QueryDocumentBM25Retriever,
    QueryQuestionRetriever,
)
from .. import parse_config
from ..reranker import BGEReranker, MergeReranker,BGEM3Reranker
from ..context_utils import contexts_trunc,retriever_results_format,documents_list_filter
from ..langchain_utils import RunnableDictAssign
from ..query_process_utils.preprocess_utils import is_api_query, language_check,query_translate,get_service_name
from ..workspace_utils import WorkspaceManager


logger = logging.getLogger('mkt_knowledge_entry')
logger.setLevel(logging.INFO)

zh_embedding_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_endpoint = os.environ.get("en_embedding_endpoint", "")
workspace_table = os.environ.get("workspace_table", "")

dynamodb = boto3.resource("dynamodb")
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)


class AppState(TypedDict):
    state: dict

# define nodes
    
def mkt_fast_reply(state: AppState):
    state_ori = state
    state = state['state']
    fast_info = state.get('fast_info',"")
    answer = state.get(
        "answer",
        "很抱歉，我只能回答与亚马逊云科技产品和服务相关的咨询。"
    )
    output = {
            "answer": answer,
            "sources": [],
            "contexts": [],
            "context_docs": [],
            "context_sources": []
    }
    logger.info(f'mkt_fast_reply: {fast_info}')
    state_ori['state'] = output
    return state_ori


def conversation_query_rewrite(state: AppState):
    state_ori = state
    state = state['state']

    rag_config = state['rag_config']
    conversation_query_rewrite_config = rag_config['query_process_config']['conversation_query_rewrite_config']
    
    cqr_llm_chain = LLMChain.get_chain(
        intent_type=CONVERSATION_SUMMARY_TYPE,
        **conversation_query_rewrite_config
    )
    conversation_summary_chain = chain_logger(
        RunnableBranch(
            (
                lambda x: not x['chat_history'],
                RunnableLambda(lambda x: x['query'])
            ),
            cqr_llm_chain
        ),
        "conversation_summary_chain",
        log_output_template='conversation_summary_chain result: {output}',
        message_id=state['message_id']
    )
   
    state['conversation_query_rewrite'] = conversation_summary_chain.invoke(state)

    return state_ori 


def query_preprocess(state: AppState):
    state_ret = state 
    state = state['state']
    rag_config = state['rag_config']
    translate_config = rag_config['query_process_config']['translate_config']
    translate_chain = RunnableLambda(
        lambda x: query_translate(
                  x['query'],
                  lang=x['query_lang'],
                  translate_config=translate_config
                  )
        )
    lang_check_and_translate_chain = RunnablePassthrough.assign(
        query_lang = RunnableLambda(lambda x:language_check(x['query']))
    )  | RunnablePassthrough.assign(translated_text=translate_chain)
    
    is_api_query_chain = RunnableLambda(lambda x:is_api_query(x['query']))
    service_names_recognition_chain = RunnableLambda(lambda x:get_service_name(x['query']))
    
    preprocess_chain = lang_check_and_translate_chain | RunnableParallelAssign(
        is_api_query=is_api_query_chain,
        service_names=service_names_recognition_chain
    )

    log_output_template=dedent("""
                               preprocess result:
                               query_lang: {query_lang}
                               translated_text: {translated_text}
                               is_api_query: {is_api_query} 
                               service_names: {service_names}
                            """)
    preprocess_chain = chain_logger(
        preprocess_chain,
        'preprocess chain',
        message_id=state['message_id'],
        log_output_template=log_output_template
    )
    state = preprocess_chain.invoke(state)
    state_ret['state'] = state
    return state_ret


def get_intent_recognition_with_index_chain(state):
    
    intent_recognition_index = IntentRecognitionAOSIndex(
        embedding_endpoint_name=state['intent_embedding_endpoint_name'])
    intent_index_ingestion_chain = chain_logger(
        intent_recognition_index.as_ingestion_chain(),
        "intent_index_ingestion_chain",
        message_id=state['message_id']
    )
    intent_index_check_exist_chain = RunnablePassthrough.assign(
        is_intent_index_exist = intent_recognition_index.as_check_index_exist_chain()
    )
    intent_index_search_chain = chain_logger(
        intent_recognition_index.as_search_chain(top_k=5),
        "intent_index_search_chain",
        message_id=state['message_id']
    )
    inten_postprocess_chain = intent_recognition_index.as_intent_postprocess_chain(method='top_1')
    
    intent_search_and_postprocess_chain = intent_index_search_chain | inten_postprocess_chain
    intent_branch = RunnableBranch(
        (lambda x: not x['is_intent_index_exist'], intent_index_ingestion_chain | intent_search_and_postprocess_chain),
        intent_search_and_postprocess_chain
    )
    intent_recognition_index_chain = intent_index_check_exist_chain | intent_branch
    return intent_recognition_index_chain


def get_qq_match_chain(state):
    # qq_match
    qq_workspace_list = state['qq_workspace_list']
    rag_config = state['rag_config']
    
    qq_match_threshold = rag_config['retriever_config']['qq_config']['qq_match_threshold']
    qq_retriever_top_k = rag_config['retriever_config']['qq_config']['retriever_top_k']
    retriever_list = [
        QueryQuestionRetriever(
            workspace,
            # index=index["name"],
            # vector_field=index["vector_field"],
            # source_field=index["source_field"],
            size=qq_retriever_top_k,
            # lang=index["lang"],
            # embedding_model_endpoint=index["embedding_endpoint"]
        )
        for workspace in qq_workspace_list
    ]
    qq_chain = MergerRetriever(retrievers=retriever_list) | \
                RunnableLambda(retriever_results_format) |\
                RunnableLambda(partial(
                    documents_list_filter,
                    threshold=qq_match_threshold
                ))
    return qq_chain


def qq_match_and_intent_recognition(state):
    state_ret = state
    state = state['state']
    qq_chain = get_qq_match_chain(state)
    intent_recognition_chain= get_intent_recognition_with_index_chain(state)
    
    log_output_template=dedent("""
        qq_result num: {qq_result_num}
        intent recognition type: {intent_type}
    """)
    qq_and_intention_type_recognition_chain = chain_logger(
        RunnableParallelAssign(
            qq_result=qq_chain,
            intent_type=intent_recognition_chain,
        ) | RunnablePassthrough.assign(qq_result_num=lambda x:len(x['qq_result'])),
        "qq_and_intention_type_recognition_chain",
        log_output_template=log_output_template,
        message_id=state['message_id']
    )

    state = qq_and_intention_type_recognition_chain.invoke(state)
    state_ret['state'] = state
    return state_ret


def qd_retriver(state):
    state_ret = state
    state = state['state']
    rag_config = state['rag_config']
    qd_config = rag_config['retriever_config']['qd_config']                     
    using_whole_doc = qd_config['using_whole_doc']
    context_num = qd_config['context_num']
    retriever_top_k = qd_config['retriever_top_k']
    reranker_top_k = qd_config['reranker_top_k']
    qd_query_key = qd_config['query_key']
    reranker_type = qd_config['reranker_type']
    
    qd_workspace_list = state['qd_workspace_list']

    retriever_list = [
        QueryDocumentKNNRetriever(
            workspace=workspace,
            using_whole_doc=using_whole_doc,
            context_num=context_num,
            top_k=retriever_top_k,
            query_key=qd_query_key
            #   "zh", zh_embedding_endpoint
        )
        for workspace in qd_workspace_list
    ]

    lotr = MergerRetriever(retrievers=retriever_list)

    if reranker_type == RerankerType.BGE_RERANKER.value:
        compressor = BGEReranker(query_key=qd_query_key)
    elif reranker_type == RerankerType.BGE_M3_RERANKER.value:
        compressor = BGEM3Reranker()
    else:
        compressor = MergeReranker()
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    qd_chain = RunnablePassthrough.assign(
        docs=compression_retriever | RunnableLambda(retriever_results_format)
        )
    state = qd_chain.invoke(state)
    state_ret['state'] = state
    return state_ret 


def context_filter(state):
    state_ret = state
    state = state['state']
    rag_config = state['rag_config']
    qd_match_threshold = rag_config['retriever_config']['qd_config']['qd_match_threshold']
    filtered_docs = documents_list_filter(state['docs'],filter_key='score',threshold=qd_match_threshold)
    state['filtered_docs'] = filtered_docs 
    return state_ret


def llm(state):
    state_ret = state
    state = state['state']
    message_id = state['message_id']
    stream = state['stream']
    rag_config = state['rag_config']
    generator_llm_config = rag_config['generator_llm_config']
    context_num = generator_llm_config['context_num']
    llm_chain = RunnableDictAssign(lambda x: contexts_trunc(x['docs'],context_num=context_num)) |\
          RunnablePassthrough.assign(
               answer=LLMChain.get_chain(
                    intent_type=IntentType.KNOWLEDGE_QA.value,
                    stream=stream,
                    **generator_llm_config
                    ),
                chat_history=lambda x:rag_config['chat_history']
          )

    llm_chain = chain_logger(llm_chain,'llm_chain', message_id=message_id)
    state = llm_chain.invoke(state)
    state_ret['state'] = state
    return state_ret


# conditional edge
def decide_intent(state):
    state = state['state']
    allow_intents = [
        IntentType.KNOWLEDGE_QA.value,
        IntentType.MARKET_EVENT.value
        ]
    
    if len(state['qq_result']) > 0:
        state['answer'] = sorted(state['qq_result'],key=lambda x:x['score'],reverse=True)[0]['answer']
        state['fast_info'] = 'qq_matched'
        return 'mkt_fast_reply'
    
    if state['intent_type'] not in allow_intents:
        state['fast_info'] = f"unsupported intent type: {state['intent_type']}"
        return 'mkt_fast_reply'

    return 'qd_retriver'


def decide_if_context_sufficient(state):
    state = state['state']
    if not state['filtered_docs']:
        state['fast_info'] = ' insufficient context to answer the question'
        return 'mkt_fast_reply'
    return 'llm'
    

def market_chain_knowledge_entry(
    query_input: str,
    stream=False,
    manual_input_intent=None,
    event_body=None,
    rag_config=None,
    message_id=None
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.
    :param stream(Bool): Whether to use llm stream decoding output.
    return: answer(str)
    """
    if rag_config is None:
        rag_config = parse_config.parse_mkt_entry_knowledge_config(event_body)

    assert rag_config is not None

    logger.info(f'market rag knowledge configs:\n {json.dumps(rag_config,indent=2,ensure_ascii=False,cls=JSONEncoder)}')

    workspace_ids = rag_config["retriever_config"]["workspace_ids"]
    qq_workspace_list = []
    qd_workspace_list = []
    for workspace_id in workspace_ids:
        workspace = workspace_manager.get_workspace(workspace_id)
        if not workspace or "index_type" not in workspace:
            logger.warning(f"workspace {workspace_id} not found")
            continue
        if workspace["index_type"] == "qq":
            qq_workspace_list.append(workspace)
        else:
            qd_workspace_list.append(workspace)


    debug_info = {}
    contexts = []
    sources = []
    answer = ""

    workflow = StateGraph(AppState)
    workflow.add_node('mkt_fast_reply',mkt_fast_reply)
    workflow.add_node('conversation_query_rewrite',conversation_query_rewrite)
    workflow.add_node('query_preprocess',query_preprocess)
    workflow.add_node('qq_match_and_intent_recognition',qq_match_and_intent_recognition)
    workflow.add_node('qd_retriver',qd_retriver)
    workflow.add_node('context_filter',context_filter)
    workflow.add_node('llm',llm)
 
    # start node
    workflow.set_entry_point("conversation_query_rewrite")
    # termial node
    workflow.add_edge('mkt_fast_reply', END)
    workflow.add_edge('llm', END)

    # norm edge
    workflow.add_edge('conversation_query_rewrite','query_preprocess')
    workflow.add_edge(
        'query_preprocess',
        'qq_match_and_intent_recognition'
        )
     
    workflow.add_edge('qd_retriver','context_filter')
    
    # conditional edges
    workflow.add_conditional_edges(
        'qq_match_and_intent_recognition',
        decide_intent,
        {
        "mkt_fast_reply": "mkt_fast_reply",
        "qd_retriver": "qd_retriver"
    })

    workflow.add_conditional_edges(
         "context_filter",
         decide_if_context_sufficient,
         {
             "mkt_fast_reply":'mkt_fast_reply',
             "llm":"llm"
         }
     )

    app = workflow.compile()
    app.get_graph().print_ascii()

    inputs = {
            "query": query_input,
            "debug_info": debug_info,
            # "intent_type": intent_type,
            # "intent_info": intent_info,
            "chat_history": rag_config['chat_history'],
            "rag_config": rag_config,
            "message_id": message_id,
            "stream": stream,
            "qq_workspace_list": qq_workspace_list,
            "qd_workspace_list": qd_workspace_list,
            "intent_embedding_endpoint_name": os.environ['intent_recognition_embedding_endpoint']
            # "query_lang": "zh"
        }
    response = app.invoke({'state':inputs})['state']
    # response = asyncio.run(full_chain.ainvoke(
    #     {
    #         "query": query_input,
    #         "debug_info": debug_info,
    #         # "intent_type": intent_type,
    #         # "intent_info": intent_info,
    #         "chat_history": rag_config['chat_history'],
    #         # "query_lang": "zh"
    #     }
    # ))

    answer = response["answer"]
    sources = response["context_sources"]
    contexts = response["context_docs"]

    return answer, sources, contexts, debug_info