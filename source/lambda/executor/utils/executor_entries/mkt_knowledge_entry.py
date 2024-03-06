import logging 
import json 
import os
from functools import partial 

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
from ..langchain_utils import chain_logger,RunnableDictAssign,RunnableParallelAssign
from ..constant import IntentType, CONVERSATION_SUMMARY_TYPE
import asyncio

from ..retriever import (
    QueryDocumentRetriever,
    QueryQuestionRetriever,
    index_results_format_and_filter
)
from .. import parse_config
from ..reranker import BGEReranker, MergeReranker
from ..context_utils import contexts_trunc
from ..langchain_utils import RunnableDictAssign


logger = logging.getLogger('mkt_knowledge_entry')
logger.setLevel(logging.INFO)

zh_embedding_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_endpoint = os.environ.get("en_embedding_endpoint", "")

def mkt_fast_reply(answer="很抱歉，我只能回答与亚马逊云科技产品和服务相关的咨询。"):
    output = {
            "answer": answer,
            "sources": [],
            "contexts": [],
            "context_docs": [],
            "context_sources": []
    }
    logger.info(f'mkt_fast_reply, answer: {answer}')
    return output
    
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

    # generator_llm_config = rag_config['generator_llm_config']
    # intent_type = rag_config['intent_config']['intent_type']
    aos_index_dict = json.loads(os.environ["aos_index_dict"])
        
    aos_index_mkt_qd = aos_index_dict["aos_index_mkt_qd"]
    aos_index_mkt_qq_name = aos_index_dict["aos_index_mkt_qq"]
    aos_index_dgr_qd = aos_index_dict["aos_index_dgr_qd"]
    aos_index_dgr_faq_qd = aos_index_dict["aos_index_dgr_faq_qd"]
    aos_index_dgr_qq_name = aos_index_dict["aos_index_dgr_qq"]

    debug_info = {}
    contexts = []
    sources = []
    answer = ""
    intent_info = {
        "manual_input_intent": manual_input_intent,
        "strict_qq_intent_result": {},
    }


    """
    # step 1 conversation summary chain, rewrite query involve history conversation
    """
    conversation_query_rewrite_config = rag_config['query_process_config']['conversation_query_rewrite_config']
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
            query=cqr_llm_chain
        ),
        "conversation_summary_chain",
        log_output_template='conversation_summary_chain result: {query}.',
        message_id=message_id
    )


    """
    # step 2.1 intent recognition chain 
    """
    intent_recognition_index = IntentRecognitionAOSIndex(embedding_endpoint_name=zh_embedding_endpoint)
    intent_index_ingestion_chain = chain_logger(
        intent_recognition_index.as_ingestion_chain(),
        "intent_index_ingestion_chain",
        message_id=message_id
    )
    intent_index_check_exist_chain = RunnablePassthrough.assign(
        is_intent_index_exist = intent_recognition_index.as_check_index_exist_chain()
    )
    intent_index_search_chain = chain_logger(
        intent_recognition_index.as_search_chain(top_k=5),
        "intent_index_search_chain",
        message_id=message_id
    )
    inten_postprocess_chain = intent_recognition_index.as_intent_postprocess_chain(method='top_1')
    
    intent_search_and_postprocess_chain = intent_index_search_chain | inten_postprocess_chain
    intent_branch = RunnableBranch(
        (lambda x: not x['is_intent_index_exist'], intent_index_ingestion_chain | intent_search_and_postprocess_chain),
        intent_search_and_postprocess_chain
    )
    intent_recognition_chain = intent_index_check_exist_chain | intent_branch
    

    """
    # step 2.2 qq match
    """
    aos_index_dgr_qq = {
        "name": aos_index_dgr_qq_name,
        "lang": "zh",
        "embedding_endpoint": zh_embedding_endpoint,
        "source_field": "source",
        "vector_field": "vector_field" 
    }
    aos_index_mkt_qq = {
        "name": aos_index_mkt_qq_name,
        "lang": "zh",
        "embedding_endpoint": zh_embedding_endpoint,
        "source_field": "file_path",
        "vector_field": "vector_field" 
    }
    q_q_match_threshold = rag_config['retriever_config']['q_q_match_threshold']
    retriever_list = [
        QueryQuestionRetriever(
            index=index["name"],
            vector_field=index["vector_field"],
            source_field=index["source_field"],
            size=5,
            lang=index["lang"],
            embedding_model_endpoint=index["embedding_endpoint"]
        )
        for index in [aos_index_dgr_qq, aos_index_mkt_qq]
    ]
    qq_chain =  MergerRetriever(retrievers=retriever_list) | RunnableLambda(
        partial(
            index_results_format_and_filter,
            threshold=q_q_match_threshold
        ))
    # qq_chain = RunnablePassthrough.assign(qq_result=qq_chain)
    # qq_chain = chain_logger(
    #     qq_chain, 
    #     'qq_chain',
    #     log_output_template="qq chain match num: {len(qq_result)}"
    # )

    """
    # step 3 qd retriever chain
    """
    qd_aos_index_list = [aos_index_dgr_qd, aos_index_dgr_faq_qd, aos_index_mkt_qd]
    using_whole_doc = rag_config['retriever_config']['using_whole_doc']
    chunk_num = rag_config['retriever_config']['chunk_num']
    retriever_top_k = rag_config['retriever_config']['retriever_top_k']
    reranker_top_k = rag_config['retriever_config']['reranker_top_k']
    enable_reranker = rag_config['retriever_config']['enable_reranker']

    retriever_list = [
        QueryDocumentRetriever(
            index, "vector_field", "text", "file_path", using_whole_doc, chunk_num, retriever_top_k, "zh", zh_embedding_endpoint
        )
        for index in qd_aos_index_list
    ]
    #  + [
    #     QueryDocumentRetriever(
    #         index, "vector_field", "text", "file_path", using_whole_doc, chunk_num, retriever_top_k, "en", en_embedding_endpoint
    #     )
    #     for index in qd_aos_index_list
    # ]
    lotr = MergerRetriever(retrievers=retriever_list)
    if enable_reranker:
        compressor = BGEReranker(top_n=reranker_top_k)
    else:
        compressor = MergeReranker(top_n=reranker_top_k)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=lotr
    )
    qd_chain = RunnablePassthrough.assign(docs=compression_retriever) 
    
    """
    # step 4 llm chain
    """
    generator_llm_config = rag_config['generator_llm_config']
    context_num = generator_llm_config['context_num']
    qd_match_threshold = rag_config['retriever_config']['qd_match_threshold']
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

    qd_fast_reply_branch = RunnableBranch(
        (
            lambda x: not index_results_format_and_filter(x['docs'],threshold=qd_match_threshold),
            RunnableLambda(lambda x: mkt_fast_reply())
        ),
        llm_chain
    )

    rag_chain = qd_chain | qd_fast_reply_branch

    qq_and_intention_type_recognition_chain = chain_logger(
        RunnableParallelAssign(
            qq_result=qq_chain,
            intent_type=intent_recognition_chain
        ),
        "qq_and_intention_type_recognition_chain",
        log_output_template='\nqq_result num: {qq_result},intent recognition type: {intent_type}',
        message_id=message_id
    )

    qq_and_intent_fast_reply_branch = RunnableBranch(
        (lambda x: len(x['qq_result']) > 0, 
         RunnableLambda(
            lambda x: mkt_fast_reply(
                sorted(answer = x['qq_result'],key=lambda x:x['score'],reversed=True)[0]['answer']
                ))
        ),
        (lambda x: x['intent_type'] != IntentType.KNOWLEDGE_QA.value,RunnableLambda(lambda x: mkt_fast_reply())),
        rag_chain
    )

    full_chain = conversation_summary_chain | qq_and_intention_type_recognition_chain | qq_and_intent_fast_reply_branch
    # logger.info(f'chain dag graph: {full_chain.get_graph()}')

    response = asyncio.run(full_chain.ainvoke(
        {
            "query": query_input,
            "debug_info": debug_info,
            # "intent_type": intent_type,
            "intent_info": intent_info,
            "chat_history": rag_config['chat_history'],
            "query_lang": "zh"
        }
    ))

    answer = response["answer"]
    sources = response["context_sources"]
    contexts = response["context_docs"]

    return answer, sources, contexts, debug_info