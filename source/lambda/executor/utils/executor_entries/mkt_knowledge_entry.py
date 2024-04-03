import logging 
import json 
import os
import boto3
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
from ..intent_utils import IntentRecognitionAOSIndex
from ..llm_utils import LLMChain
from ..serialization_utils import JSONEncoder
from ..logger_utils import get_logger
from ..langchain_utils import (
    chain_logger,
    RunnableDictAssign,
    RunnableParallelAssign,
    format_trace_infos
)
from ..constant import IntentType, CONVERSATION_SUMMARY_TYPE, RerankerType
import asyncio

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
    is_query_too_short,
    query_clean,
    rule_based_query_expansion
)
from ..workspace_utils import WorkspaceManager


logger = get_logger('mkt_knowledge_entry')

# zh_embedding_endpoint = os.environ.get("zh_embedding_endpoint", "")
# en_embedding_endpoint = os.environ.get("en_embedding_endpoint", "")

intent_recognition_embedding_endpoint = os.environ.get("intent_recognition_embedding_endpoint", "")
workspace_table = os.environ.get("workspace_table", "")

dynamodb = boto3.resource("dynamodb")
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)


def mkt_fast_reply(
        x,
        answer=None,
        fast_info="",
        debug_info=None,
       
    ):
    intent_type = x.get('intent_type', IntentType.KNOWLEDGE_QA.value)
    if answer is None:
        answer="很抱歉，我只能回答与亚马逊云科技产品和服务相关的咨询。"
        if intent_type == IntentType.MARKET_EVENT.value:
            answer = "抱歉，我没有查询到相关的市场活动信息。"

    output = {
            "answer": answer,
            "sources": [],
            "contexts": [],
            "context_docs": [],
            "context_sources": []
    }
    if debug_info is not None:
        debug_info['response_msg'] = fast_info
    logger.info(f'mkt_fast_reply: {fast_info}')
    return output


def get_qd_chain(qd_config, qd_workspace_list):
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
        "qd chain",
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


def market_chain_knowledge_entry(
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
    event_workspace_ids = rag_config["retriever_config"]["event_workspace_ids"]
    qq_workspace_list, qd_workspace_list = get_workspace_list(workspace_ids)
    event_qq_workspace_list, event_qd_workspace_list = get_workspace_list(event_workspace_ids)

    # logger.info(f"qq_workspace_list: {qq_workspace_list}\nqd_workspace_list: {qd_workspace_list}")

    debug_info = {
        "response_msg": "normal"
        }
    contexts = []
    sources = []
    answer = ""
    trace_infos = []
    # intent_info = {
    #     "manual_input_intent": manual_input_intent,
    #     "strict_qq_intent_result": {},
    # }

    ######################
    # step 0 query reject#
    ######################
    query_length_threshold = rag_config['query_process_config']['query_length_threshold']
    is_query_too_short_chain = RunnablePassthrough.assign(
        is_query_too_short = RunnableLambda(
        lambda x:is_query_too_short(x['query'],threshold=query_length_threshold)
    ))


    ################################################################################
    # step 1 conversation summary chain, rewrite query involve history conversation#
    ################################################################################
    
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
        log_output_template=f'conversation_summary_chain result: {"{"+conversation_query_rewrite_result_key+"}"}',
        message_id=message_id,
        trace_infos=trace_infos
    )

    #######################
    # step 2 query preprocess#
    #######################
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
        'preprocess query chain',
        message_id=message_id,
        log_output_template=log_output_template,
        trace_infos=trace_infos
    )

    #####################################
    # step 3.1 intent recognition chain #
    #####################################
    intent_recognition_index = IntentRecognitionAOSIndex(
        embedding_endpoint_name=intent_recognition_embedding_endpoint
        )
    intent_index_ingestion_chain = chain_logger(
        intent_recognition_index.as_ingestion_chain(),
        "intent_index_ingestion_chain",
        message_id=message_id,
        trace_infos=trace_infos
    )
    intent_index_check_exist_chain = RunnablePassthrough.assign(
        is_intent_index_exist = intent_recognition_index.as_check_index_exist_chain()
    )
    intent_index_search_chain = chain_logger(
        intent_recognition_index.as_search_chain(top_k=5),
        "intent_index_search_chain",
        message_id=message_id,
        trace_infos=trace_infos
    )
    intent_postprocess_chain = intent_recognition_index.as_intent_postprocess_chain(method='top_1')
    
    intent_search_and_postprocess_chain = intent_index_search_chain | intent_postprocess_chain
    intent_branch = RunnableBranch(
        (lambda x: not x['is_intent_index_exist'], intent_index_ingestion_chain | intent_search_and_postprocess_chain),
        intent_search_and_postprocess_chain
    )
    intent_recognition_chain = intent_index_check_exist_chain | intent_branch
    
    ####################
    # step 3.2 qq match#
    ####################
    qq_match_threshold = rag_config['retriever_config']['qq_config']['qq_match_threshold']
    qq_retriver_top_k = rag_config['retriever_config']['qq_config']['retriever_top_k']
    qq_query_key = rag_config['retriever_config']['qq_config']['query_key']
    qq_enable_debug = rag_config['retriever_config']['qq_config']['enable_debug']
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
        qq_compressor = BGEReranker(query_key=qq_query_key)
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

    ############################
    # step 4. qd retriever chain#
    ############################
    qd_config = rag_config['retriever_config']['qd_config']                     
    qd_chain = get_qd_chain(qd_config, qd_workspace_list)
    event_qd_chain = get_qd_chain(qd_config, event_qd_workspace_list)
    
    #####################
    # step 5. llm chain #
    #####################
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

    # llm_chain = chain_logger(llm_chain,'llm_chain', message_id=message_id)

    ###########################
    # step 6 synthesize chain #
    ###########################
     
    ######################
    # step 6.1 rag chain #
    ######################
    qd_match_threshold = rag_config['retriever_config']['qd_config']['qd_match_threshold']
    qd_fast_reply_branch = RunnablePassthrough.assign(
        filtered_docs = RunnableLambda(lambda x: documents_list_filter(x['docs'],filter_key='rerank_score',threshold=qd_match_threshold))
    ) | RunnableBranch(
        (
            lambda x: not x['filtered_docs'],
            RunnableLambda(lambda x: mkt_fast_reply(
                x,
                fast_info="insufficient context",
                debug_info=debug_info
            ))
        ),
        llm_chain
    )

    qd_chain = RunnableBranch(
            (
                lambda x: x['intent_type'] == IntentType.MARKET_EVENT.value, 
                event_qd_chain
            ),
            qd_chain  
        )

    rag_chain = chain_logger(
        qd_chain | qd_fast_reply_branch,
        'rag chain',
        trace_infos=trace_infos
    )

    ######################################
    # step 6.2 fast reply based on intent#
    ######################################
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
        message_id=message_id,
        trace_infos=trace_infos
    )
    
    allow_intents = [
        IntentType.KNOWLEDGE_QA.value,
        IntentType.MARKET_EVENT.value
        ]
    qq_and_intent_fast_reply_branch = RunnableBranch(
        (lambda x: len(x['qq_result']) > 0, 
         RunnableLambda(
            lambda x: mkt_fast_reply(
                x,
                answer=sorted(x['qq_result'],key=lambda x:x['score'],reverse=True)[0]['answer'],
                fast_info='qq matched',
                debug_info=debug_info
                ))
        ),
        (
            lambda x: x['intent_type'] not in allow_intents, 
            RunnableLambda(lambda x: mkt_fast_reply(
                x,
                fast_info=f"unsupported intent type: {x['intent_type']}",
                debug_info=debug_info
                ))
        ),
        RunnablePassthrough.assign(query=RunnableLambda(lambda x: rule_based_query_expansion(x['query']))) | rag_chain
    )

    #######################
    # step 6.3 full chain #
    #######################

    process_query_chain = conversation_summary_chain | preprocess_chain

    process_query_chain = chain_logger(
        process_query_chain,
        "query process module",
        message_id=message_id,
        trace_infos=trace_infos
    )

    qq_and_intent_fast_reply_branch = chain_logger(
        qq_and_intent_fast_reply_branch,
        "retrieve module",
        message_id=message_id,
        trace_infos=trace_infos
    )

    full_chain =  process_query_chain | qq_and_intention_type_recognition_chain | qq_and_intent_fast_reply_branch
    
    full_chain = is_query_too_short_chain |  RunnableBranch(
        (
            lambda x:x['is_query_too_short'],
            RunnableLambda(lambda x: mkt_fast_reply(
                x,
                fast_info=f"query: `{x['query']}` is too short",
                # answer=f"问题长度小于{query_length_threshold}，请详细描述问题。",
                answer=f"您好，我是亚麻小Q，请详细描述您的问题。",
                debug_info=debug_info
                ))
        ),
        full_chain
    )

    # full_chain = chain_logger(
    #     full_chain,
    #     'full_chain',
    #     trace_infos=trace_infos
    # )
    # start_time = time.time()

    response = asyncio.run(full_chain.ainvoke(
        {
            "query": query_input,
            "debug_info": debug_info,
            # "intent_type": intent_type,
            # "intent_info": intent_info,
            "chat_history": rag_config['chat_history'] if rag_config['use_history'] else [],
            # "query_lang": "zh"
        }
    ))
    # print('invoke time',time.time()-start_time)
    answer = response["answer"]
    sources = response["context_sources"]
    contexts = response["context_docs"]
    trace_info = format_trace_infos(trace_infos)
    
    logger.info(f'session_id: {rag_config["session_id"]}, chain trace info:\n{trace_info}')

    return answer, sources, contexts, debug_info