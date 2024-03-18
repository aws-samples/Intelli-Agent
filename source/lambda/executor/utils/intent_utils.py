import json
import os
import re
import traceback
from functools import partial
from random import Random

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)

from . import retriever
from .constant import INTENT_RECOGNITION_TYPE, IntentType
from .langchain_utils import chain_logger
from .llm_utils import Model as LLM_Model
from .llm_utils.llm_chains import LLMChain
from .preprocess_utils import get_service_name, is_api_query
from .prompt_template import (
    INTENT_RECOGINITION_EXAMPLE_TEMPLATE,
    INTENT_RECOGINITION_PROMPT_TEMPLATE_CLUADE,
)
from .retriever import (
    QueryDocumentRetriever,
    QueryQuestionRetriever,
    index_results_format,
)

abs_file_dir = os.path.dirname(__file__)

# intent_map = {
#     "闲聊": IntentType.CHAT.value,
#     "知识问答": IntentType.KNOWLEDGE_QA.value
# }


class IntentUtils:
    def __init__(
        self,
        intent_save_path=os.path.join(abs_file_dir, "intent_examples/examples.json"),
        example_template=INTENT_RECOGINITION_EXAMPLE_TEMPLATE,
        llm_model_id="anthropic.claude-v2:1",
        llm_model_kwargs={
            "temperature": 0,
            "max_tokens": 2000,
            "stop_sequences": ["\n\n", "\n\nHuman:"],
        },
        seed=42,
    ):
        self.intent_few_shot_examples = json.load(open(intent_save_path))
        self.intent_indexs = {
            intent_d["intent"]: intent_d["index"]
            for intent_d in self.intent_few_shot_examples["intents"]
        }
        self.index_intents = {v: k for k, v in self.intent_indexs.items()}
        self.intents = list(self.intent_few_shot_examples["examples"].keys())
        self.few_shot_examples = self.create_few_shot_examples()
        Random(seed).shuffle(self.few_shot_examples)
        self.examples_str = self.create_few_shot_example_string(
            example_template=example_template
        )
        self.categories_str = self.create_all_labels_string()
        self.intent_recognition_template = PromptTemplate.from_template(
            INTENT_RECOGINITION_PROMPT_TEMPLATE_CLUADE
        )
        self.llm = LLM_Model.get_model(llm_model_id, model_kwargs=llm_model_kwargs)
        self.intent_recognition_llm_chain = self.intent_recognition_template | self.llm

    def create_few_shot_examples(self):
        ret = []
        for intent in self.intents:
            examples = self.intent_few_shot_examples["examples"][intent]
            for query in examples:
                ret.append({"intent": intent, "query": query})
        return ret

    def create_few_shot_example_string(
        self, example_template=INTENT_RECOGINITION_EXAMPLE_TEMPLATE
    ):
        example_strs = []
        intent_indexs = self.intent_indexs
        for example in self.few_shot_examples:
            example_strs.append(
                example_template.format(
                    label=intent_indexs[example["intent"]], query=example["query"]
                )
            )
        return "\n\n".join(example_strs)

    def create_all_labels_string(self):
        intent_few_shot_examples = self.intent_few_shot_examples
        label_strs = []
        labels = intent_few_shot_examples["intents"]
        for i, label in enumerate(labels):
            label_strs.append(f"({label['index']}) {label['describe']}")
        return "\n".join(label_strs)

    def postprocess(self, output: str):
        out = output.strip()
        assert out, output
        return self.index_intents[out[0]]


intention_obj = IntentUtils()

# def create_few_shot_example_string(examples):
#     example_strs = []
#     for example in examples:
#         example_strs.append(
#             INTENT_RECOGINITION_EXAMPLE_TEMPLATE.format(
#                 label=example['label'],
#                 query=example['query']
#                 )
#         )
#     return '\n'.join(example_strs)

# def create_all_labels_string(labels):
#     label_strs = []
#     for i,label in enumerate(labels):
#         label_strs.append(f"- {label}")
#     return "\n".join(label_strs)


# def postprocess(output:str):
#     output = f'<category>{output}'
#     r = re.findall('<category>(.*?)</category>',output,re.S)
#     assert r, output
#     r = [rr.strip() for rr in r]
#     r = [rr for rr in r if rr]
#     assert r, output
#     return r[0]


def get_intent_with_claude(query, intent_if_fail, debug_info):
    predict_label = None
    try:
        r = intention_obj.intent_recognition_llm_chain.invoke(
            {
                "categories": intention_obj.categories_str,
                "examples": intention_obj.examples_str,
                "query": query,
            }
        )
        predict_label = intention_obj.postprocess(r)
    except:
        print(traceback.format_exc())
        predict_label

    intent = predict_label or intent_if_fail
    debug_info["intent_debug_info"] = {
        "llm_output": r,
        "origin_intent": predict_label,
        "intent": intent,
    }
    return intent


# def get_intent(query,intent_type,qq_index=None):
#     assert IntentType.has_value(intent_type),intent_type
#     if intent_type != IntentType.AUTO:
#         return intent_type

# return get_intent_with_claude(query)

# def auto_intention_recoginition_chain(
#         index_q_q,
#         lang="zh",
#         embedding_endpoint="",
#         q_q_match_threshold=0.9,
#         intent_if_fail=IntentType.KNOWLEDGE_QA.value
#     ):
#     """

#     Args:
#         index_q_q (_type_): _description_
#         q_q_match_threshold (float, optional): _description_. Defaults to 0.9.
#     """
#     def get_custom_intent_type(x):
#         assert IntentType.has_value(x["intent_type"]), x["intent_type"]
#         return x["intent_type"]

#     def get_strict_intent(x):
#         x["intent_type"] = IntentType.STRICT_QQ.value
#         x["intent_info"]["strict_qq_intent_result"] = x["q_q_match_res"]["answer"]
#         return x["intent_type"]

#     q_q_retriever = QueryQuestionRetriever(
#         index=index_q_q, vector_field="vector_field", source_field="file_path", size=5, lang=lang, embedding_model_endpoint=embedding_endpoint)

#     strict_q_q_chain = q_q_retriever | RunnableLambda(partial(index_results_format,threshold=0))


#     intent_type_auto_recognition_chain = RunnablePassthrough.assign(
#         q_q_match_res=strict_q_q_chain
#     ) | RunnableBranch(
#         # (lambda x: len(x['q_q_match_res']["answer"]) > 0, RunnableLambda(lambda x: IntentType.STRICT_QQ.value)),
#         (
#             lambda x: x['q_q_match_res']["answer"][0]["score"] < q_q_match_threshold and x["intent_type"] == IntentType.AUTO.value,
#             RunnableLambda(lambda x: get_intent_with_claude(x['query'],intent_if_fail,x['debug_info']))
#         ),
#         RunnableLambda(lambda x: get_strict_intent(x))
#     )

#     intent_type_chain = RunnablePassthrough.assign(
#         intent_type=RunnableBranch(
#             (
#                 lambda x:x["intent_type"] == IntentType.AUTO.value or x["intent_type"] == IntentType.STRICT_QQ.value,
#                 intent_type_auto_recognition_chain
#             ),
#             RunnableLambda(get_custom_intent_type)
#         )
#     )

#     # add 2nd stage intent chain here, e.g. knowledge_qa
#     sub_intent_chain = RunnablePassthrough.assign(
#           is_api_query = RunnableLambda(lambda x:is_api_query(x['query'])),
#           service_names = RunnableLambda(lambda x:get_service_name(x['query']))
#     )
#     sub_intent_chain = chain_logger(
#         sub_intent_chain,
#         "sub intent chain",
#         log_output_template='\nis_api_query: {is_api_query}.\nservice_names: {service_names}'
#     )

#     chain = intent_type_chain | RunnableBranch(
#         (lambda x:x["intent_type"] == IntentType.KNOWLEDGE_QA.value, sub_intent_chain),
#         RunnablePassthrough()
#     )

#     return chain


def get_intent_with_llm(query, intent_if_fail, debug_info, intent_config):
    chain = LLMChain.get_chain(
        **{**intent_config, "intent_type": INTENT_RECOGNITION_TYPE}
    )
    predict_label = None
    error_str = None
    try:
        predict_label = chain.invoke({"query": query})
    except:
        error_str = traceback.format_exc()
        print(error_str)

    intent = predict_label or intent_if_fail
    debug_info["intent_debug_info"] = {
        "llm_output": predict_label,
        "origin_intent": predict_label,
        "intent": intent,
        "error": error_str,
    }
    return intent


def auto_intention_recoginition_chain(
    q_q_retriever_config=None,
    intent_config=None,
    # index_q_q,
    # lang="zh",
    # embedding_endpoint="",
    # q_q_match_threshold=0.9,
    intent_if_fail=IntentType.KNOWLEDGE_QA.value,
    message_id=None,
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
        index=q_q_retriever_config["index_q_q"],
        vector_field="vector_field",
        source_field="file_path",
        size=5,
        lang=q_q_retriever_config["lang"],
        embedding_model_endpoint=q_q_retriever_config["embedding_endpoint"],
    )

    strict_q_q_chain = q_q_retriever | RunnableLambda(
        partial(index_results_format, threshold=0)
    )

    q_q_match_threshold = q_q_retriever_config["q_q_match_threshold"]
    intent_type_auto_recognition_chain = RunnablePassthrough.assign(
        q_q_match_res=strict_q_q_chain
    ) | RunnableBranch(
        # (lambda x: len(x['q_q_match_res']["answer"]) > 0, RunnableLambda(lambda x: IntentType.STRICT_QQ.value)),
        (
            lambda x: x["q_q_match_res"]["answer"][0]["score"] < q_q_match_threshold
            and x["intent_type"] == IntentType.AUTO.value,
            RunnableLambda(
                lambda x: get_intent_with_llm(
                    x["query"],
                    intent_if_fail,
                    x["debug_info"],
                    intent_config=intent_config,
                )
            ),
        ),
        RunnableLambda(lambda x: get_strict_intent(x)),
    )

    intent_type_chain = RunnablePassthrough.assign(
        intent_type=RunnableBranch(
            (
                lambda x: x["intent_type"] == IntentType.AUTO.value
                or x["intent_type"] == IntentType.STRICT_QQ.value,
                intent_type_auto_recognition_chain,
            ),
            RunnableLambda(get_custom_intent_type),
        )
    )

    # add 2nd stage intent chain here, e.g. knowledge_qa
    sub_intent_chain = RunnablePassthrough.assign(
        is_api_query=RunnableLambda(lambda x: is_api_query(x["query"])),
        service_names=RunnableLambda(lambda x: get_service_name(x["query"])),
    )
    sub_intent_chain = chain_logger(
        sub_intent_chain,
        "sub intent chain",
        log_output_template="\nis_api_query: {is_api_query}.\nservice_names: {service_names}",
        message_id=message_id,
    )

    chain = intent_type_chain | RunnableBranch(
        (lambda x: x["intent_type"] == IntentType.KNOWLEDGE_QA.value, sub_intent_chain),
        RunnablePassthrough(),
    )

    return chain


# intent_recognition_with_opensearch
def create_opensearch_index(opensearch_client):
    pass


def intent_recognition_with_openserach_chain(opensearch_client, top_k=5):
    pass
