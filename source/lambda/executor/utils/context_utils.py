import logging
from langchain.docstore.document import Document
import os

from .time_utils import timeit

logger = logging.getLogger("context_utils")
logger.setLevel(logging.INFO)


def contexts_trunc(docs: list[dict], context_num=2):
    # print('docs len',len(docs))
    docs = [doc for doc in docs[:context_num]]
    # the most related doc will be placed last
    docs.sort(key=lambda x: x["score"])
    logger.info(f'max context score: {docs[-1]["score"]}')
    # filter same docs
    s = set()
    context_strs = []
    context_docs = []
    context_sources = []
    for doc in docs:
        content = doc["page_content"]
        if content not in s:
            context_strs.append(content)
            s.add(content)
            context_docs.append(
                {"doc": content, "source": doc["source"], "score": doc["score"]}
            )
            context_sources.append(doc["source"])
    # print(len(context_docs))
    # print(sg)
    return {
        "contexts": context_strs,
        "context_docs": context_docs,
        "context_sources": context_sources,
    }


@timeit
def retriever_results_format(
    docs: list[Document],
    print_source=True,
    print_content=os.environ.get("print_content", False),
):
    doc_dicts = []

    for doc in docs:
        doc_dicts.append(
            {
                "page_content": doc.page_content,
                "retrieval_score": doc.metadata["retrieval_score"],
                "rerank_score": doc.metadata["score"],
                "score": doc.metadata["score"],
                "source": doc.metadata["source"],
                "answer": doc.metadata.get("answer", ""),
                "question": doc.metadata.get("question", ""),
            }
        )
    if print_source:
        source_strs = []
        for doc_dict in doc_dicts:
            content = ""
            if print_content:
                content = f', content: {doc_dict["page_content"]}'
            source_strs.append(
                f'source: {doc_dict["source"]}, score: {doc_dict["score"]}{content}, retrieval score: {doc_dict["retrieval_score"]}'
            )
        logger.info("retrieved sources:\n" + "\n".join(source_strs))
    return doc_dicts


def documents_list_filter(doc_dicts: list[dict], filter_key="score", threshold=-1):
    results = []
    for doc_dict in doc_dicts:
        if doc_dict[filter_key] < threshold:
            continue
        results.append(doc_dict)

    return results
