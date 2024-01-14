from langchain import hub
import re
from llm_utils import Model as LLM_Model
from langchain.schema.runnable import RunnableLambda


def query_rewrite_postprocess(r):
    ret = re.findall('<questions>.*?</questions>',r,re.S)[0]
    questions  = re.findall('- (.*?)\n',ret,re.S)
    return questions


def get_query_rewrite_chain(
        llm_model_id,
        model_kwargs=None,
        query_expansion_template="hwchase17/multi-query-retriever"
    ):
    query_expansion_template = hub.pull(query_expansion_template)
    llm = LLM_Model.get_model(model_id=llm_model_id, model_kwargs=model_kwargs)
    chain = RunnableLambda(lambda x: query_expansion_template.invoke({"question": x["query"]})) | llm | RunnableLambda(query_rewrite_postprocess)
    return chain

def get_conversation_query_rewrite_chain():
    pass