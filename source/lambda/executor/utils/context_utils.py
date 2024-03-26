import logging
from langchain.docstore.document import Document
import os

from .time_utils import timeit
from .logger_utils import get_logger
import pandas as pd 

logger = logging.getLogger('context_utils')

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
            content = doc['page_content']
            if content not in s:
                context_strs.append(content)
                s.add(content)
                context_docs.append({
                    "doc": content,
                    "source": doc["source"],
                    "score": doc["score"]
                    })
                context_sources.append(doc["source"])
        # print(len(context_docs))
        # print(sg)
        return {
            "contexts": context_strs,
            "context_docs": context_docs,
            "context_sources":context_sources
        }


def retriever_results_format(
          docs:list[Document],
          print_source=True,
          print_content=os.environ.get('print_content',False)
          ):
    doc_dicts = []

    for doc in docs:
        doc_dicts.append({
             "page_content": doc.page_content,
            #  "retrieval_score": doc.metadata["retrieval_score"], 
            #  "rerank_score": doc.metadata["score"], 
            **doc.metadata
            #  "source": doc.metadata["source"],
            #  "answer": doc.metadata.get("answer",""),
            # "question": doc.metadata.get("question",""),
            })
    
    if not doc_dicts:
        return doc_dicts
    cols = list(doc_dicts[0].keys())
    if not print_content:
        cols = [col for col in cols if 'content' not in col and 'answer' not in col]
    print_strs = []
    for doc_dict in doc_dicts:
        print_strs.append(', '.join([f'{col}: {doc_dict[col]}' for col in cols]))
    s = '\n'.join(print_strs)

    logger.info( "retrieved source infos: \n" + f"{s}")
    
    return doc_dicts

def documents_list_filter(doc_dicts:list[dict],filter_key='score',threshold=-1):
    results = []
    for doc_dict in doc_dicts:
        if doc_dict[filter_key] < threshold:
            continue
        results.append(doc_dict)

    return results
    
     
     
     