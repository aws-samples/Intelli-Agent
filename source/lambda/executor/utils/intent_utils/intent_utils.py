from  .. import retriever
from ..retriever import QueryDocumentRetriever, QueryQuestionRetriever,index_results_format
from ..constant import IntentType,INTENT_RECOGNITION_TYPE
from functools import partial
from langchain.schema.runnable import RunnablePassthrough, RunnableBranch, RunnableLambda
# from ..llm_utils import Model as LLM_Model
from ..llm_utils.llm_chains import LLMChain
# from langchain.prompts import PromptTemplate
import re 
import traceback
# from ..prompt_template import INTENT_RECOGINITION_PROMPT_TEMPLATE_CLUADE,INTENT_RECOGINITION_EXAMPLE_TEMPLATE
import os 
import json 
from random import Random
from ..query_process_utils.preprocess_utils import is_api_query,get_service_name
from ..langchain_utils import chain_logger

abs_file_dir = os.path.dirname(__file__)


def get_intent_with_llm(query,intent_if_fail,debug_info,intent_config):
    chain = LLMChain.get_chain(
        **{**intent_config,"intent_type":INTENT_RECOGNITION_TYPE}
    )
    predict_label = None
    error_str = None
    try:
        predict_label = chain.invoke({
            "query": query
        })
    except:
        error_str = traceback.format_exc()
        print(error_str)
    
    intent = predict_label or intent_if_fail
    debug_info['intent_debug_info'] = {
        'llm_output': predict_label,
        'origin_intent': predict_label,
        'intent': intent,
        'error': error_str
        }
    return intent


def auto_intention_recoginition_chain(
        q_q_retriever_config = None,
        intent_config=None,
        # index_q_q,
        # lang="zh",
        # embedding_endpoint="",
        # q_q_match_threshold=0.9,
        intent_if_fail=IntentType.KNOWLEDGE_QA.value,
        message_id=None
    ):
    """

    Args:
        index_q_q (_type_): _description_
        q_q_match_threshold (float, optional): _description_. Defaults to 0.9.
    """
    assert q_q_retriever_config is not None and intent_config is not None
    def get_custom_intent_type(x):
        assert IntentType.has_value(x["intent_type"]), x["intent_type"]
        return x["intent_type"]
    
    def get_strict_intent(x):
        x["intent_type"] = IntentType.STRICT_QQ.value
        x["intent_info"]["strict_qq_intent_result"] = x["q_q_match_res"]["answer"]
        return x["intent_type"]
    
    
    q_q_retriever = QueryQuestionRetriever(
        index=q_q_retriever_config['index_q_q'],
        vector_field="vector_field", 
        source_field="file_path", 
        size=5, 
        lang=q_q_retriever_config['lang'],
        embedding_model_endpoint=q_q_retriever_config['embedding_endpoint']
    )
     
    strict_q_q_chain = q_q_retriever | RunnableLambda(partial(index_results_format,threshold=0))
    
    q_q_match_threshold = q_q_retriever_config['q_q_match_threshold']
    intent_type_auto_recognition_chain = RunnablePassthrough.assign(
        q_q_match_res=strict_q_q_chain
    ) | RunnableBranch(
        # (lambda x: len(x['q_q_match_res']["answer"]) > 0, RunnableLambda(lambda x: IntentType.STRICT_QQ.value)),
        (
            lambda x: x['q_q_match_res']["answer"][0]["score"] < q_q_match_threshold and x["intent_type"] == IntentType.AUTO.value,
            RunnableLambda(lambda x: get_intent_with_llm(x['query'],intent_if_fail,x['debug_info'],intent_config=intent_config))
        ),
        RunnableLambda(lambda x: get_strict_intent(x))
    )

    intent_type_chain = RunnablePassthrough.assign(
        intent_type=RunnableBranch(
            (
                lambda x:x["intent_type"] == IntentType.AUTO.value or x["intent_type"] == IntentType.STRICT_QQ.value,
                intent_type_auto_recognition_chain
            ),
            RunnableLambda(get_custom_intent_type)
        )
    )

    # add 2nd stage intent chain here, e.g. knowledge_qa
    sub_intent_chain = RunnablePassthrough.assign(
          is_api_query = RunnableLambda(lambda x:is_api_query(x['query'])),
          service_names = RunnableLambda(lambda x:get_service_name(x['query']))
    ) 
    sub_intent_chain = chain_logger(
        sub_intent_chain,
        "sub intent chain",
        log_output_template='\nis_api_query: {is_api_query}.\nservice_names: {service_names}',
        message_id=message_id
    )

    chain = intent_type_chain | RunnableBranch(
        (lambda x:x["intent_type"] == IntentType.KNOWLEDGE_QA.value, sub_intent_chain),
        RunnablePassthrough()
    )     

    return chain


# intent_recognition_with_opensearch
def create_opensearch_index(opensearch_client):
    pass


def intent_recognition_with_openserach_chain(opensearch_client,top_k=5):
    pass

    
    








