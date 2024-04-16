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
    is_query_too_short
)
from ..db_utils.sql_utils import (
    check_sql_validation
)
from ..workspace_utils import WorkspaceManager


logger = logging.getLogger('mkt_knowledge_entry')
logger.setLevel(logging.INFO)

abs_file_dir = os.path.dirname(__file__)
intent_example_path = os.path.join(
    abs_file_dir,
    "../intent_utils",
    "intent_examples",
    "text2sql_examples.json"
)

zh_embedding_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_endpoint = os.environ.get("en_embedding_endpoint", "")

intent_recognition_embedding_endpoint = os.environ.get("intent_recognition_embedding_endpoint", "")
workspace_table = os.environ.get("workspace_table", "")

dynamodb = boto3.resource("dynamodb")
workspace_table = dynamodb.Table(workspace_table)
workspace_manager = WorkspaceManager(workspace_table)


def text2sql_fast_reply(
        x,
        answer=None,
        fast_info="",
        debug_info=None,
       
    ):
    intent_type = x.get('intent_type', IntentType.KNOWLEDGE_QA.value)
    if intent_type == IntentType.CHAT.value:
        answer="抱歉，我只能回答与text2sql相关的咨询。"
    elif intent_type == IntentType.COMMON_QUICK_REPLY_TOO_SHORT.value:
        answer="请详细描述您的问题。"
    else:
        answer=f"错误意图识别!: {intent_type}"
        # if intent_type == IntentType.MARKET_EVENT.value:
        #     answer = "抱歉，我没有查询到相关的市场活动信息。"

    output = {
            "answer": answer,
            "intent_type": intent_type,
            "sources": [],
            "contexts": [],
            "context_docs": [],
            "context_sources": []
    }
    if debug_info is not None:
        debug_info['response_msg'] = fast_info
    logger.info(f'text2sql_fast_reply: {fast_info}')
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
            query_key=qd_query_key
            #   "zh", zh_embedding_endpoint
        )
        for workspace in qd_workspace_list
    ] + [QueryDocumentBM25Retriever(
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


def text2sql_guidance_entry(
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
        rag_config = parse_config.parse_text2sql_entry_config(event_body)

    assert rag_config is not None

    logger.info(f'text2sql rag knowledge configs:\n {json.dumps(rag_config,indent=2,ensure_ascii=False,cls=JSONEncoder)}')

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

    ####################################################################################################
    # construct basic chains #
    ####################################################################################################
    # 1st chain: rule_check_chain
    # purpose: quick check rules according to text2sql requirements
    # 1. text2sql quick rule check: text2sql_rule_check_func
    # 1.1 whether the query is too short: is_query_too_short_func
    query_length_threshold = rag_config['query_process_config']['query_length_threshold']
    is_query_too_short_func = RunnablePassthrough.assign(
        is_query_too_short = RunnableLambda(
        lambda x:is_query_too_short(x['query'],threshold=query_length_threshold)
    ))
    text2sql_rule_check_func = is_query_too_short_func

    rule_check_chain = RunnableBranch(
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_RE_GEN.value,
            # placeholder for RAG in re-generation case
            RunnablePassthrough()
        ),
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_GEN.value, 
            text2sql_rule_check_func | RunnableBranch(
                (lambda x: x['is_query_too_short'],
                    RunnablePassthrough.assign(intent_type=RunnableLambda(
                        lambda x: IntentType.COMMON_QUICK_REPLY_TOO_SHORT.value))),
                RunnablePassthrough()
            )
        ),
        # bypass according to intentions
        RunnablePassthrough(),
    )

    # 2nd chain: process_query_chain
    # purpose: process query before retrieve
    # 1. convseration_summary_func
    conversation_query_rewrite_config = rag_config['query_process_config']['conversation_query_rewrite_config']
    conversation_query_rewrite_result_key = conversation_query_rewrite_config['result_key']
    cqr_llm = LLMChain.get_chain(
        intent_type=CONVERSATION_SUMMARY_TYPE,
        **conversation_query_rewrite_config
    )
    cqr_llm = RunnableBranch(
        # single turn
        (lambda x: not x['chat_history'],RunnableLambda(lambda x:x['query'])),
        cqr_llm
    )
    conversation_summary_func = RunnablePassthrough.assign(
            **{conversation_query_rewrite_result_key:cqr_llm}
            # query=cqr_llm_chain
        )
    # 2. preprocess_qurey_func
    translate_config = rag_config['query_process_config']['translate_config']
    translate_func = RunnableLambda(
        lambda x: query_translate(
                  x['query'],
                  lang=x['query_lang'],
                  translate_config=translate_config
                  )
        )
    lang_check_and_translate_chain = RunnablePassthrough.assign(
        query_lang = RunnableLambda(lambda x:language_check(x['query']))
    )  | RunnablePassthrough.assign(translated_text=translate_func)
    
    is_api_query_func = RunnableLambda(lambda x:is_api_query(x['query']))
    service_names_recognition_func = RunnableLambda(lambda x:get_service_name(x['query']))
    
    preprocess_query_func = lang_check_and_translate_chain | RunnableParallelAssign(
        is_api_query=is_api_query_func,
        service_names=service_names_recognition_func
    )

    process_query_chain = RunnableBranch(
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_RE_GEN.value,
            # placeholder for re-process in re-generation case
            RunnablePassthrough()
        ),
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_GEN.value,
            # placeholder for re-process in re-generation case
            conversation_summary_func | preprocess_query_func
        ),
        # bypass according to intentions
        RunnablePassthrough(),
    )

    # 3rd chain: retrieve_and_intention_chain
    # purpose: retrieve index and decide the intention
    # 1. qurey-and-query match function: qq_match_func
    qq_match_threshold = rag_config['retriever_config']['qq_config']['qq_match_threshold']
    qq_retriver_top_k = rag_config['retriever_config']['qq_config']['retriever_top_k']
    qq_query_key = rag_config['retriever_config']['qq_config']['query_key']
    retriever_list = [
        QueryQuestionRetriever(
            workspace,
            size=qq_retriver_top_k,
            query_key=qq_query_key
        )
        for workspace in qq_workspace_list
    ]
    if len(qq_workspace_list):
        qq_compressor = BGEReranker(query_key=qq_query_key)
        qq_lotr = MergerRetriever(retrievers=retriever_list)
        qq_compression_retriever = ContextualCompressionRetriever(
            base_compressor=qq_compressor, base_retriever=qq_lotr
        )
        qq_match_func =  chain_logger(
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
        qq_match_func = RunnableLambda(lambda x:[])
    # 2. intention match according to aos retrieve: intent_aos_retrieve_func
    intent_recognition_index = IntentRecognitionAOSIndex(
        embedding_endpoint_name=intent_recognition_embedding_endpoint,
        intent_example_path=intent_example_path
        )
    intent_index_ingestion = chain_logger(
        intent_recognition_index.as_ingestion_chain(),
        "intent_index_ingestion",
        message_id=message_id,
        trace_infos=trace_infos
    )
    intent_index_check_exist = RunnablePassthrough.assign(
        is_intent_index_exist = intent_recognition_index.as_check_index_exist_chain()
    )
    intent_index_search = chain_logger(
        intent_recognition_index.as_search_chain(top_k=5),
        "intent_index_search_chain",
        message_id=message_id,
        trace_infos=trace_infos
    )
    intent_postprocess = intent_recognition_index.as_intent_postprocess_chain(method='top_1')
    
    intent_search_and_postprocess = intent_index_search | intent_postprocess
    intent_branch = RunnableBranch(
        (lambda x: not x['is_intent_index_exist'], intent_index_ingestion | intent_search_and_postprocess),
        intent_search_and_postprocess
    )
    intent_aos_match_func = intent_index_check_exist | intent_branch

    # 3. query-and-document match function: qd_match_func
    qd_match_threshold = rag_config['retriever_config']['qd_config']['qd_match_threshold']
    qd_config = rag_config['retriever_config']['qd_config']                     
    qd_match_func = get_qd_chain(qd_config, qd_workspace_list)
    # event_qd_chain = get_qd_chain(qd_config, event_qd_workspace_list)
    qd_match_func = RunnableBranch(
            (
                # place holder for dedicate search function (TODO)
                lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_GEN.value, 
                qd_match_func
            ),
            qd_match_func
        )

    retrieve_and_intention_chain = RunnableBranch(
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_RE_GEN.value,
            # placeholder for RAG in re-generation case
            RunnablePassthrough()
        ),
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_GEN.value, 
            RunnableParallelAssign(
                qq_result=qq_match_func,
                intent_type=intent_aos_match_func,
            ) | RunnablePassthrough.assign(qq_result_num=lambda x:len(x['qq_result'])) | \
                RunnableBranch(
                    (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_GEN.value,
                        qd_match_func
                    ),
                    # fast reply intentions
                    RunnablePassthrough(),
                ),
        ),
        # bypass according to intentions
        RunnablePassthrough(),
    )

    # 4th chain: text2sql_llm_chain
    # purpose: generate sql according to retrieve contents 
    # 1. generate sql 1st time
    # 2. dedicate llm for re-generating sql according to error message (TODO): current is still same llm as the gen llm
    generator_llm_config = rag_config['generator_llm_config']
    context_num = generator_llm_config['context_num']

    text2sql_llm_chain = RunnableBranch(
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_RE_GEN.value,
            RunnablePassthrough.assign(
                answer=LLMChain.get_chain(
                    intent_type=IntentType.TEXT2SQL_SQL_RE_GEN.value,
                    stream=stream,
                    **generator_llm_config
                    ),
                chat_history=lambda x:rag_config['chat_history']
          )
        ),
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_GEN.value, 
            RunnableDictAssign(lambda x: contexts_trunc(x['docs'],context_num=context_num)) |\
            RunnablePassthrough.assign(
                answer=LLMChain.get_chain(
                    intent_type=IntentType.TEXT2SQL_SQL_GEN.value,
                    stream=stream,
                    **generator_llm_config
                    ),
                chat_history=lambda x:rag_config['chat_history']
          )
        ),
        RunnablePassthrough(),
    )

    # 5th chain: post_process_chain
    # main function: run generated sql using api, to validate the qulity of sql
    # 1. run sql using asana api: is_sql_validated
    # 2. generate post process message accoding to non gen or re-gen intention: text2sql_fast_reply
    post_process_chain = RunnableBranch(
        (lambda x: x['intent_type'] == IntentType.TEXT2SQL_SQL_RE_GEN.value or x['intent_type'] == IntentType.TEXT2SQL_SQL_GEN.value, 
            RunnablePassthrough.assign(
                sql_validate_result = RunnableLambda(
                lambda x:check_sql_validation(x['answer'])
            )) | RunnableBranch(
                (
                    lambda x:x['sql_validate_result']=='Passed',
                    RunnablePassthrough.assign(intent_type=lambda x: IntentType.TEXT2SQL_SQL_VALIDATED.value)
                ),
                RunnablePassthrough.assign(intent_type=lambda x: IntentType.TEXT2SQL_SQL_RE_GEN.value)
            )
        ),
        RunnableLambda(
            lambda x: text2sql_fast_reply(
                x,
                # answer=sorted(x['qq_result'],key=lambda x:x['score'],reverse=True)[0]['answer'],
                # fast_info='qq matched',
                debug_info=debug_info
        )),
    )

    ####################################################################################################
    # add log to separate chains and construct full chain #
    ####################################################################################################
    rule_check_chain =  chain_logger(
        rule_check_chain,
        'rule_check_chain',
        message_id=message_id,
    )

    log_output_template=dedent("""
                                conversation_summary_chain results: {conversation_query_rewrite_result_key},
                                preprocess result:
                                query_lang: {query_lang}
                                translated_text: {translated_text}
                                is_api_query: {is_api_query} 
                                service_names: {service_names}
                            """)

    process_query_chain =  chain_logger(
        process_query_chain,
        'process_query_chain',
        message_id=message_id,
        log_output_template=log_output_template,
        trace_infos=trace_infos
    )

    retrieve_and_intention_chain =  chain_logger(
        retrieve_and_intention_chain,
        'retrieve_and_intention_chain',
        message_id=message_id,
    )

    text2sql_llm_chain =  chain_logger(
        text2sql_llm_chain,
        'text2sql_llm_chain',
        message_id=message_id,
    )

    post_process_chain =  chain_logger(
        post_process_chain,
        'post_process_chain',
        message_id=message_id,
    )
    
    full_chain = rule_check_chain | process_query_chain | retrieve_and_intention_chain | text2sql_llm_chain | post_process_chain

    ####################################################################################################
    # async invoke full chain in a while loop#
    ####################################################################################################
    cont = True
    chain_try_num = 0
    max_try_num = rag_config["generator_llm_config"]["llm_max_try_num"]
    intent_type = IntentType.TEXT2SQL_SQL_GEN.value

    sql_validate_result = ""
    contexts = ""
    chat_history = rag_config['chat_history'] if rag_config['use_history'] else []
    while(cont):

        response = asyncio.run(full_chain.ainvoke(
            {
                "query": query_input,
                "debug_info": debug_info,
                "intent_type": intent_type,
                "chat_history": chat_history,
                "sql_validate_result": sql_validate_result,
                "contexts": contexts
            }
        ))

        # print('invoke time',time.time()-start_time)
        trace_info = format_trace_infos(trace_infos)

        logger.info(f'chain trace info:\n{trace_info}')

        if response["intent_type"] == IntentType.TEXT2SQL_SQL_GEN.value:
            # validated sql output
            cont = False
            answer = response["answer"].split("<query>")[1].split("</query>")[0]
            try:
            except:
                answer = response["answer"]
            sources = response["context_sources"]
        elif response["intent_type"] == IntentType.TEXT2SQL_SQL_RE_GEN.value:
            # fast reply
        if response["intent_type"] != IntentType.TEXT2SQL_SQL_RE_GEN.value:
            # 1. fast reply intent
            # 2. validated sql output
            cont = False
            try:
                answer = response["answer"].split("<query>")[1].split("</query>")[0]
            except:
                answer = response["answer"]
            sources = response["context_sources"]
        elif chain_try_num == max_try_num:
            cont = False
        else:
            # sql validated fail, re-generate
            intent_type = response["intent_type"]
            sql_validate_result = response["sql_validate_result"]
            try:
                answer = response["answer"].split("<query>")[1].split("</query>")[0]
            except:
                answer = response["answer"]

            chat_history = [f"""
            This is error message of generated wrong SQL query: 

            {sql_validate_result}. 

            To correct this, please generate an alternative SQL query which will correct the syntax error.
            The updated query should take care of all the syntax issues encountered.
            Follow the instructions mentioned above to remediate the error. 
            Update the below generated wrong SQL query to resolve the issue:

            <wrong_sql_query>
            {answer}
            </wrong_sql_query>

            Make sure the updated SQL query aligns with the requirements provided in the following question.
            Think about your answer first before you respond. Put your response in <query></query> tags.
            """]
            contexts = response["contexts"]
        
        chain_try_num = chain_try_num + 1


    return answer, sources, contexts, debug_info