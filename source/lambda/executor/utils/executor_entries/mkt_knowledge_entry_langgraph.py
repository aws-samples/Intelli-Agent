import logging 
import json 
import os
import boto3
from datetime import datetime
import time
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
from langgraph.graph import StateGraph,END
from ..intent_utils import IntentRecognitionAOSIndex
from ..llm_utils import LLMChain
from ..time_utils import get_china_now

from ..serialization_utils import JSONEncoder
from ..logger_utils import get_logger
from ..langchain_utils import (
    chain_logger,
    RunnableDictAssign,
    RunnableParallelAssign,
    format_trace_infos
)
from ..constant import IntentType, CONVERSATION_SUMMARY_TYPE, RerankerType,MKT_QUERY_REWRITE_TYPE
import asyncio
from typing import TypedDict,Any,List,Dict

from ..retriever import (
    QueryDocumentKNNRetriever,
    QueryDocumentBM25Retriever,
    QueryQuestionRetriever
)
from .. import parse_config
from ..reranker import BGEReranker, MergeReranker, BGEM3Reranker
from ..context_utils import contexts_trunc,retriever_results_format,documents_list_filter
from ..langchain_utils import RunnableDictAssign
from ..query_process_utils.preprocess_utils import (
    is_api_query, 
    language_check,
    query_translate,
    get_service_name,
    is_query_invalid,
    query_clean,
    rule_based_query_expansion
)
from ..workspace_utils import WorkspaceManager
from ..constant import MKTUserType

logger = get_logger('mkt_knowledge_entry')

intent_recognition_embedding_endpoint = os.environ.get("intent_recognition_embedding_endpoint", "")
workspace_table = os.environ.get("workspace_table", "")

dynamodb = boto3.resource("dynamodb")
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)


# fast reply
QUERY_INVALID = "请重新描述您的问题。请注意：\n不能过于简短也不能超过500个字符\n不能包含个人信息（身份证号、手机号等）"
INVALID_INTENT = "很抱歉，我只能回答与亚马逊云科技产品和服务相关的咨询。"
KNOWLEDGE_QA_INSUFFICIENT_CONTEXT = "很抱歉，根据我目前掌握到的信息无法给出回答。"
EVENT_INSUFFICIENT_CONTEXT = "抱歉，我没有查询到相关的市场活动信息。"

class AppState(TypedDict):
    keys: Any

def get_qd_chain(qd_config, qd_workspace_list,state):
    using_whole_doc = qd_config['using_whole_doc']
    context_num = qd_config['context_num']
    retriever_top_k = qd_config['retriever_top_k']
    # reranker_top_k = qd_config['reranker_top_k']
    # enable_reranker = qd_config['enable_reranker']
    reranker_type = qd_config['reranker_type']
    qd_query_key = qd_config['query_key']
    retriever_list = [
        QueryDocumentKNNRetriever(
            workspace=workspace,
            using_whole_doc=using_whole_doc,
            context_num=context_num,
            top_k=retriever_top_k,
            query_key=qd_query_key,
            enable_debug=qd_config['enable_debug']
            #   "zh", zh_embedding_endpoint
        )
        for workspace in qd_workspace_list
    ] + [QueryDocumentBM25Retriever(
            workspace=workspace,
            using_whole_doc=using_whole_doc,
            context_num=context_num,
            top_k=retriever_top_k,
            query_key=qd_query_key,
            enable_debug=qd_config['enable_debug']
            #   "zh", zh_embedding_endpoint
        )
        for workspace in qd_workspace_list
    ]

    lotr = MergerRetriever(retrievers=retriever_list)
    if reranker_type == RerankerType.BGE_RERANKER.value:
        compressor = BGEReranker(query_key=qd_query_key, enable_debug=qd_config['enable_debug'])
    elif reranker_type == RerankerType.BGE_M3_RERANKER.value:
        compressor = BGEM3Reranker()
    else:
        compressor = MergeReranker()

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    qd_chain = chain_logger(
        RunnablePassthrough.assign(
        docs=compression_retriever | RunnableLambda(retriever_results_format)
        ),
        "retrieve module",
        trace_infos=state['trace_infos']
    )
    return qd_chain


def get_workspace_list(workspace_ids):
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
    return qq_workspace_list, qd_workspace_list



################
# define nodes #
################

def mkt_fast_reply(
        state
    ):
    
    state = state['keys']
    fast_info = state.get('fast_info',"")
    debug_info = state['debug_info']
    answer = state['answer']
    context_sources = state.get('context_sources', [])
    intent_type = state.get('intent_type', IntentType.KNOWLEDGE_QA.value)
    if answer is None:
        answer="很抱歉，我只能回答与亚马逊云科技产品和服务相关的咨询。"
        if intent_type == IntentType.MARKET_EVENT.value:
            answer = "抱歉，我没有查询到相关的市场活动信息。"

    output = {
            "answer": answer,
            # "sources": [],
            "contexts": [],
            "context_docs": [],
            "context_sources": context_sources
    }
    if debug_info is not None:
        debug_info['response_msg'] = fast_info 
    logger.info(f'mkt_fast_reply: {fast_info}')
    state.update(output)


######################
# step 0 query reject#
######################

def query_reject(state:AppState):
    state = state['keys']
    rag_config = state['rag_config']
    query_length_threshold = rag_config['query_process_config']['query_length_threshold']

    state['is_query_invalid'] = is_query_invalid(
        state['query'],
        threshold=query_length_threshold
    )
    

################################################################################
# step 1 conversation summary chain, rewrite query involve history conversation#
################################################################################

def conversation_query_rewrite(state: AppState):
    state = state['keys']
    rag_config = state['rag_config']
    message_id = state['message_id']
    trace_infos = state['trace_infos']
    conversation_query_rewrite_config = rag_config['query_process_config']['conversation_query_rewrite_config']
    conversation_query_rewrite_result_key = conversation_query_rewrite_config['result_key']
    cqr_llm_chain = LLMChain.get_chain(
        intent_type=CONVERSATION_SUMMARY_TYPE,
        **conversation_query_rewrite_config
    )
    cqr_llm_chain = RunnableBranch(
        # single turn
        (lambda x: not x['chat_history'],RunnableLambda(lambda x:x['query'])),
        cqr_llm_chain
    )

    conversation_summary_chain = chain_logger(
        RunnablePassthrough.assign(
            **{conversation_query_rewrite_result_key:cqr_llm_chain}
            # query=cqr_llm_chain
        ),
        "conversation_summary_chain",
        log_output_template=f'conversation_summary_chain result:<conversation_summary> {"{"+conversation_query_rewrite_result_key+"}"}</conversation_summary>',
        message_id=message_id,
        trace_infos=trace_infos
    )
    
    _state = conversation_summary_chain.invoke(state)
    state.update(**_state)


##########################
# step 2 query preprocess#
##########################
def query_preprocess(state: AppState):
    state = state['keys']
    rag_config = state['rag_config']
    message_id = state['message_id']
    trace_infos = state['trace_infos']

    translate_config = rag_config['query_process_config']['translate_config']
    translate_chain = RunnableLambda(
        lambda x: query_translate(
                  x['query'],
                  lang=x['query_lang'],
                  translate_config=translate_config
                  )
        )
    query_clean_chain = RunnablePassthrough.assign(
        query=RunnableLambda(lambda x: query_clean(x['query']))
        )
    lang_check_and_translate_chain = RunnablePassthrough.assign(
        query_lang = RunnableLambda(lambda x:language_check(x['query']))
    )  | RunnablePassthrough.assign(translated_text=translate_chain)
    
    is_api_query_chain = RunnableLambda(lambda x:is_api_query(x['query']))
    service_names_recognition_chain = RunnableLambda(lambda x:get_service_name(x['query']))
    
    
    preprocess_chain = query_clean_chain | lang_check_and_translate_chain | RunnableParallelAssign(
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
        'query process module',
        message_id=message_id,
        log_output_template=log_output_template,
        trace_infos=trace_infos
    )
    
    _state = preprocess_chain.invoke(state)
    state.update(_state)


#####################################
# step 3.1 intent recognition chain #
#####################################
# EMBEDDING_ENDPOINT_NAME = ""


def get_intent_recognition_with_index_chain(state):
    rag_config = state['rag_config']
    conversation_query_rewrite_config = rag_config['query_process_config']['conversation_query_rewrite_config']
    conversation_query_rewrite_result_key = conversation_query_rewrite_config['result_key']
    
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
        intent_recognition_index.as_search_chain(top_k=5,query_key=conversation_query_rewrite_result_key),
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


####################
# step 3.2 qq match#
####################

def get_qq_match_chain(state):
    rag_config = state['rag_config']
    qq_match_threshold = rag_config['retriever_config']['qq_config']['qq_match_threshold']
    qq_retriver_top_k = rag_config['retriever_config']['qq_config']['retriever_top_k']
    qq_enable_debug = rag_config['retriever_config']['qq_config']['enable_debug']
    qq_query_key = rag_config['retriever_config']['qq_config']['query_key']
    qq_workspace_list = state['qq_workspace_list']
    trace_infos = state['trace_infos']
    retriever_list = [
        QueryQuestionRetriever(
            workspace,
            size=qq_retriver_top_k,
            query_key=qq_query_key,
            enable_debug=qq_enable_debug
        )
        for workspace in qq_workspace_list
    ]
    if len(qq_workspace_list):
        qq_compressor = BGEReranker(query_key=qq_query_key, enable_debug=qq_enable_debug)
        qq_lotr = MergerRetriever(retrievers=retriever_list)
        qq_compression_retriever = ContextualCompressionRetriever(
            base_compressor=qq_compressor, base_retriever=qq_lotr
        )
        qq_chain =  chain_logger(
            # MergerRetriever(retrievers=retriever_list) | \
            qq_compression_retriever | \
                    RunnableLambda(retriever_results_format) |\
                    RunnableLambda(partial(
                        documents_list_filter,
                        filter_key='retrieval_score',
                        threshold=qq_match_threshold
                    ))
            ,
            'qq_chain',
            trace_infos=trace_infos
        )
    else:
        qq_chain = RunnableLambda(lambda x:[])
    
    return qq_chain


##########################################
# step 3  qq match and intent_recognition#
##########################################

def qq_match_and_intent_recognition(state):
    state = state['keys']
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
        "intention module",
        log_output_template=log_output_template,
        message_id=state['message_id'],
        trace_infos=state['trace_infos']
    )
    
    _state = qq_and_intention_type_recognition_chain.invoke(state)
    state.update(_state)


def query_expansion(state,result_key='query'):
    state = state['keys']
    rag_config = state['rag_config']
    query_rewrite_config = rag_config['query_process_config']['query_rewrite_config']
    chain = LLMChain.get_chain(**query_rewrite_config,intent_type=MKT_QUERY_REWRITE_TYPE)
    r = chain.invoke({"query":state['query'], "stream": False,"chat_history":state['chat_history']})
    state[result_key] = r
    logger.info(f'<query_expansion>query_expansion: {r}</query_expansion>')
    # state[result_key] = rule_based_query_expansion(state['query'])

########################
# step 4. qd retriever #
########################

def knowledge_qd_retriver(state):
    state = state['keys']
    rag_config = state['rag_config']
    qd_workspace_list = state['qd_workspace_list']

    qd_config = rag_config['retriever_config']['qd_config']                     
    qd_chain = get_qd_chain(qd_config, qd_workspace_list,state)
    _state = qd_chain.invoke(state)
    state.update(_state)
    

def event_qd_retriever(state):
    state = state['keys']
    rag_config = state['rag_config']
    event_qd_workspace_list = state['event_qd_workspace_list']

    qd_config = rag_config['retriever_config']['qd_config']                     
    event_qd_chain = get_qd_chain(qd_config, event_qd_workspace_list,state)
    _state = event_qd_chain.invoke(state)
    state.update(_state)


##########################
# step 5. context filter #
 #########################

def context_filter(state):
    state = state['keys']
    rag_config = state['rag_config']
    qd_match_threshold = rag_config['retriever_config']['qd_config']['qd_match_threshold']
    filtered_docs = documents_list_filter(state['docs'],filter_key='score',threshold=qd_match_threshold)
    state['filtered_docs'] = filtered_docs 
  
#####################
# step 6. llm chain #
#####################
def rag_llm(state):
    """
    if context is sufficient
    Args:
        state (_type_): _description_
    """
    state = state['keys']
    rag_config = state['rag_config']
    stream = state['stream']
    generator_llm_config = rag_config['generator_llm_config']
    context_num = generator_llm_config['context_num']
    llm_chain = RunnableDictAssign(lambda x: contexts_trunc(
        x['docs'],
        score_key="rerank_score",
        context_num=context_num
        )) \
        | RunnablePassthrough.assign(
               answer=LLMChain.get_chain(
                    intent_type=IntentType.KNOWLEDGE_QA.value,
                    stream=stream,
                    **generator_llm_config
                    ),
                chat_history=lambda x:rag_config['chat_history']
          )
    _state = llm_chain.invoke(state)
    state.update(_state)

def chat_llm(state):
    """if context is insufficient
    Args:
        state (_type_): _description_
    """
    state = state['keys']
    rag_config = state['rag_config']
    generator_llm_config = rag_config['generator_llm_config']
    stream = state['stream']

    now = get_china_now()
    date_str = now.strftime("%Y年%m月%d日")
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekdays[now.weekday()]
    meta_instruction=f"""你是一个亚马逊云科技的AI助理，你的名字是亚麻小Q。今天是{date_str},{weekday}。
你按照下面的规范回答客户的问题:
     - 如果用户表达感谢，你也要简单表达感谢。
     - 如果你不知道某个问题，请直接回答:"您好, 根据我掌握到的知识没办法回答您的问题呢？"
     - 如果用户的问题信息不够，你可以直接反问。
     - 请保证回答简洁，每次回答不超过3句话。
"""
    llm_chain = RunnablePassthrough.assign(
                answer=LLMChain.get_chain(
                    intent_type=IntentType.CHAT.value,
                    stream=stream,
                    meta_instruction=meta_instruction,
                    **generator_llm_config
                    ),
                chat_history=lambda x:rag_config['chat_history'],
                context_sources = lambda x:[],
                context_docs = lambda x:[]
          )
    
    _state = llm_chain.invoke(state)
    state.update(_state)

# conditional edge
def decide_query_reject(state):
    state = state['keys']
    if state['is_query_invalid']:
        state['fast_info'] = 'query invalid'
        state['answer'] = QUERY_INVALID
        return 'query invalid'
    return "normal"

def decide_intent(state):
    state = state['keys']
    allow_intents = [
        IntentType.KNOWLEDGE_QA.value,
        IntentType.MARKET_EVENT.value
        ]
    
    if len(state['qq_result']) > 0:
        doc = sorted(state['qq_result'],key=lambda x:x['score'],reverse=True)[0]
        state['answer'] = doc['answer']
        state['context_sources'] = [doc['source']]
        state['fast_info'] = 'qq_matched'
        return 'qq_match'
    
    if state['intent_type'] not in allow_intents:
        state['fast_info'] = f"unsupported intent type: {state['intent_type']}"
        state['answer'] = INVALID_INTENT
        return 'unsupported_intent'

    return 'valid_intent'

def decide_qd_retriver(state):
    state = state['keys']
    if state['intent_type'] == IntentType.MARKET_EVENT.value:
        return 'event_qa'
    return 'knowledge_qa'

def decide_if_context_sufficient(state):
    state = state['keys']
    if not state['filtered_docs']:
        state['fast_info'] = 'insufficient context'
        intent_type = state.get('intent_type', IntentType.KNOWLEDGE_QA.value)
        if intent_type == IntentType.MARKET_EVENT.value:
            state['answer'] = EVENT_INSUFFICIENT_CONTEXT
        else:
            state['answer'] = KNOWLEDGE_QA_INSUFFICIENT_CONTEXT
        return 'insufficient context'
    return 'sufficient context'
    
def market_chain_knowledge_entry_417(
    query_input: str,
    stream=False,
    # manual_input_intent=None,
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

    workspace_ids = rag_config["retriever_config"]["workspace_ids"]
    event_workspace_ids = rag_config["retriever_config"]["event_workspace_ids"]
    qq_workspace_list, qd_workspace_list = get_workspace_list(workspace_ids)
    event_qq_workspace_list, event_qd_workspace_list = get_workspace_list(event_workspace_ids)

    
    debug_info = {
        "response_msg": "normal"
        }

    qd_config = rag_config['retriever_config']['qd_config'] 
    qd_config['query_key'] = "query_for_qd_retrieve"
    # qd_config['query_key'] = "query"

    trace_infos = []

    workflow = StateGraph(AppState)
    workflow.add_node('mkt_fast_reply', mkt_fast_reply)
    workflow.add_node('query_reject', query_reject)
    # workflow.add_node('conversation_query_rewrite', conversation_query_rewrite)
    workflow.add_node('query_preprocess', query_preprocess)
    workflow.add_node('qq_match_and_intent_recognition', qq_match_and_intent_recognition)
    workflow.add_node('query_expansion', partial(query_expansion,result_key=qd_config['query_key']))
    workflow.add_node('knowledge_qd_retriver', knowledge_qd_retriver)
    workflow.add_node('event_qd_retriever', event_qd_retriever)
    workflow.add_node('context_filter', context_filter)
    workflow.add_node('rag_llm', rag_llm)
    workflow.add_node('chat_llm', chat_llm)
    
    # start node
    workflow.set_entry_point("query_reject")
    # termial node
    workflow.add_edge('mkt_fast_reply', END)
    workflow.add_edge('rag_llm', END)
    workflow.add_edge('chat_llm', END)


    # normal edge
    # workflow.add_edge('conversation_query_rewrite','query_preprocess')
    workflow.add_edge(
        'query_preprocess',
        'qq_match_and_intent_recognition'
        )
    workflow.add_edge('knowledge_qd_retriver','context_filter')
    workflow.add_edge('event_qd_retriever','context_filter')

    # conditional edges
    workflow.add_conditional_edges(
        "query_reject",
        decide_query_reject,
        {
           "query invalid": "mkt_fast_reply",
           "normal": "query_preprocess"
        }
    )

    workflow.add_conditional_edges(
        'qq_match_and_intent_recognition',
        decide_intent,
        {
        "unsupported_intent": "chat_llm",
        "qq_match": "mkt_fast_reply",
        "valid_intent" : "query_expansion",
        }
    )

    workflow.add_conditional_edges(
        'query_expansion',
        decide_qd_retriver,
        {
        "event_qa" : "event_qd_retriever",
        "knowledge_qa": "knowledge_qd_retriver"
        }
    )

    workflow.add_conditional_edges(
         "context_filter",
         decide_if_context_sufficient,
         {
             "insufficient context": 'chat_llm',
             "sufficient context": "rag_llm"
         }
     )

    app = workflow.compile()
    # with open('rag_workflow.png','wb') as f:
    #     f.write(app.get_graph().draw_png())

    # app.get_graph().print_ascii()

    inputs = {
            "query": query_input,
            "debug_info": debug_info,
            # "intent_type": intent_type,
            # "intent_info": intent_info,
            "chat_history": rag_config['chat_history'][-6:] if rag_config['use_history'] else [],
            "rag_config": rag_config,
            "message_id": message_id,
            "stream": stream,
            "qq_workspace_list": qq_workspace_list,
            "qd_workspace_list": qd_workspace_list,
            "event_qd_workspace_list":event_qd_workspace_list,
            "trace_infos":trace_infos,
            "intent_embedding_endpoint_name": os.environ['intent_recognition_embedding_endpoint'],
        
            # "query_lang": "zh"
        }
    response = app.invoke({"keys":inputs})['keys']

    
    trace_info = format_trace_infos(trace_infos)
    
    logger.info(f'session_id: {rag_config["session_id"]}, chain trace info:\n{trace_info}')
    
    response['rag_config'] = rag_config
    return response


def market_chain_knowledge_entry_assistant_418(
    # query_input: str,
    # stream=False,
    # manual_input_intent=None,
    event_body
    # rag_config=None,
    # message_id=None
):
    """
    Entry point for the Lambda function.

    :param query_input: The query input.
    :param aos_index: The index of the AOS engine.
    :param stream(Bool): Whether to use llm stream decoding output.
    return: answer(str)
    """
    query_input = event_body['question']
    stream = event_body['stream']
    message_id = event_body['custom_message_id']
    
    rag_config = parse_config.parse_mkt_entry_knowledge_config(event_body)

    # TODO replace chat_history with messages in assistant
    qd_config = rag_config['retriever_config']['qd_config'] 
    if rag_config['user_type'] == MKTUserType.ASSISTANT:
        qd_config['qd_match_threshold'] = -100

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

    workspace_ids = rag_config["retriever_config"]["workspace_ids"]
    event_workspace_ids = rag_config["retriever_config"]["event_workspace_ids"]
    qq_workspace_list, qd_workspace_list = get_workspace_list(workspace_ids)
    event_qq_workspace_list, event_qd_workspace_list = get_workspace_list(event_workspace_ids)

    debug_info = {
        "response_msg": "normal"
        }

    

    
    # qd_config['query_key'] = "query_for_qd_retrieve"
    # qd_config['query_key'] = "query"

    trace_infos = []

    workflow = StateGraph(AppState)
    workflow.add_node('mkt_fast_reply', mkt_fast_reply)
    workflow.add_node('query_reject', query_reject)
    workflow.add_node('conversation_query_rewrite', conversation_query_rewrite)
    workflow.add_node('query_preprocess', query_preprocess)
    workflow.add_node('qq_match_and_intent_recognition', qq_match_and_intent_recognition)
    workflow.add_node('query_expansion', partial(query_expansion,result_key=qd_config['query_key']))
    workflow.add_node('knowledge_qd_retriver', knowledge_qd_retriver)
    workflow.add_node('event_qd_retriever', event_qd_retriever)
    workflow.add_node('context_filter', context_filter)
    workflow.add_node('rag_llm', rag_llm)
    workflow.add_node('chat_llm', chat_llm)
    
    # start node
    workflow.set_entry_point("query_reject")
    # termial node
    workflow.add_edge('mkt_fast_reply', END)
    workflow.add_edge('rag_llm', END)
    workflow.add_edge('chat_llm', END)


    # normal edge
    # workflow.add_edge('conversation_query_rewrite','query_preprocess')
    workflow.add_edge(
        'query_preprocess',
        'conversation_query_rewrite'
        )
    workflow.add_edge(
        'conversation_query_rewrite',
        'qq_match_and_intent_recognition'
        )
    workflow.add_edge('knowledge_qd_retriver','context_filter')
    workflow.add_edge('event_qd_retriever','context_filter')

    # conditional edges
    workflow.add_conditional_edges(
        "query_reject",
        decide_query_reject,
        {
           "query invalid": "mkt_fast_reply",
           "normal": "query_preprocess"
        }
    )

    workflow.add_conditional_edges(
        'qq_match_and_intent_recognition',
        decide_intent,
        {
        "unsupported_intent": "chat_llm",
        "qq_match": "mkt_fast_reply",
        "valid_intent" : "query_expansion",
        }
    )

    workflow.add_conditional_edges(
        'query_expansion',
        decide_qd_retriver,
        {
        "event_qa" : "event_qd_retriever",
        "knowledge_qa": "knowledge_qd_retriver"
        }
    )

    workflow.add_conditional_edges(
         "context_filter",
         decide_if_context_sufficient,
         {
             "insufficient context": 'chat_llm',
             "sufficient context": "rag_llm"
         }
     )

    app = workflow.compile()
    # with open('rag_workflow_418.png','wb') as f:
    #     f.write(app.get_graph().draw_png())

    # app.get_graph().print_ascii()

    inputs = {
            "query": query_input,
            "debug_info": debug_info,
            # "intent_type": intent_type,
            # "intent_info": intent_info,
            "chat_history": rag_config['chat_history'][-6:] if rag_config['use_history'] else [],
            "rag_config": rag_config,
            "message_id": message_id,
            "stream": stream,
            "qq_workspace_list": qq_workspace_list,
            "qd_workspace_list": qd_workspace_list,
            "event_qd_workspace_list":event_qd_workspace_list,
            "trace_infos":trace_infos,
            "intent_embedding_endpoint_name": os.environ['intent_recognition_embedding_endpoint'],
            # "query_lang": "zh"
        }
    response = app.invoke({"keys":inputs})['keys']

    
    trace_info = format_trace_infos(trace_infos)
    
    logger.info(f'session_id: {rag_config["session_id"]}, chain trace info:\n{trace_info}')
    
    response['rag_config'] = rag_config
    return response



market_chain_knowledge_entry = market_chain_knowledge_entry_assistant_418