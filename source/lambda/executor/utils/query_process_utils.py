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
    cqr_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given a question and its context, decontextualize the question by addressing coreference and omission issues. The resulting question should retain its original meaning and be as informative as possible, and should not duplicate any previously asked questions in the context.",
        ),
        # Few shot examples
        (
            "system",
            "{cqr_context}"
        ),
        # New question
        ("user", "\n{conversational_context}\nQuestion: {question}\nRewrite: ")
    ]
)