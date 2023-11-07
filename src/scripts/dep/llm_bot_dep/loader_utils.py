import re
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Iterator, Sequence
from langchain.document_loaders.pdf import BasePDFLoader
from langchain.docstore.document import Document
import csv
from io import TextIOWrapper
# from langchain.text_splitter import MarkdownHeaderTextSplitter
# from splitter_utils import MarkdownHeaderTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# local debugging purpose
# if __name__ == "__main__":
#     markdown_document = r"""
# # Learning to Retrieve In-Context Examples for Large Language Models

# ###### Abstract

# aaaa

# ## 1 Introduction

# 1111

# ## 2 Related Work

# 2222

# ## 3 Preliminaries

# 3333

# ## 4 Methodology

# 4444

# ### Training Data Generation

# 5555

# ### Reward Modeling

# 6666

# ### Training LLM Retrievers with Knowledge Distillation

# 7777

# ### Evaluation of LLM Retrievers

# 8888

# ## 5 Experiments

# ### Evaluation Setup

# 9999

# ### Main Results

# 0000

# \begin{table}
# This is table content
# \end{table}

# ### Training Pipeline of LLM-R

# 1010

# ### Generalization Ability of LLM-R

# 1212

# ### When does LLM-R Work and When Does it Not?

# 1313

# ### Using Different LLMs for Data Generation and Task Evaluation

# 1414

# ### Scaling the Number of In-Context Examples and Retriever Size

# 1515

# ## 7 Conclusion

# 1616

# ## Limitations

# 1717

# ## References

# 1818
# """
#     markdown_splitter = MarkdownHeaderTextSplitter()

#     # construct a fake document data
#     data = [Document(page_content=markdown_document, metadata=metadata_template)]
#     md_header_splits = markdown_splitter.split_text(data[0])
#     for i, doc in enumerate(md_header_splits):
#         logger.info("content of chunk %s: %s", i, doc)

    # local pdf file in current folder
    # loader = NougatPDFLoader('1.pdf')
    # data = loader.load()
    # logger.info("raw data: %s", data)
    # md_header_splits = markdown_splitter.split_text(data[0])
    # for i, doc in enumerate(md_header_splits):
    #     logger.info("content of chunk %s: %s", i, doc)

    # official splits will be deprecated by the new MarkdownHeaderTextSplitter
    # markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    # headers_to_split_on = [
    #     ("#", "Header 1"),
    #     ("##", "Header 2"),
    # ]
    # markdown_document = "# Foo\n\n    ## Bar\n\nHi this is Jim\n\nHi this is Joe\n\n ### Boo \n\n Hi this is Lance \n\n ## Baz\n\n Hi this is Molly"
    # md_header_splits = markdown_splitter.split_text(markdown_document)

    # Char-level splits
    # from langchain.text_splitter import RecursiveCharacterTextSplitter

    # chunk_size = 250
    # chunk_overlap = 30
    # text_splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=chunk_size, chunk_overlap=chunk_overlap
    # )

    # splits = text_splitter.split_documents(md_header_splits)
    # logger.info("splits: %s", splits)
    # from typing import Generator
    # import itertools
    # from langchain.text_splitter import RecursiveCharacterTextSplitter
    # def chunk_generator(content: List[Document], chunk_size: int = 500, chunk_overlap: int = 30) -> Generator[Document, None, None]:
    #     text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    #     for document in content:
    #         splits = text_splitter.split_documents([document])
    #         # list of Document objects
    #         for split in splits:
    #             yield split
    # def batch_generator(generator, batch_size):
    #     while True:
    #         batch = list(itertools.islice(generator, batch_size))
    #         if not batch:
    #             break
    #         yield batch

    # generator = chunk_generator(md_header_splits, )
    # batches = batch_generator(generator, batch_size=10)
    # logger.info("current batch size: {} and next batch size: {}".format(len(next(batches)), len(next(batches))))
    # # note: typeof(batch)->list[Document], sizeof(batch)=batch_size
    # for batch in batches:
    #     logger.info("batch: %s", batch)


# TODO: Local debug CSV loader, remove it before release
# if __name__ == "__main__":
#     import uuid
#     import boto3
#     from datetime import datetime

#     s3 = boto3.client('s3')
#     now = datetime.now()
#     timestamp_str = now.strftime("%Y%m%d%H%M%S")
#     print(timestamp_str)
#     random_uuid = str(uuid.uuid4())[:8]
#     print(random_uuid)

#     def process_csv(csv_content: str, kwargs):
#         bucket_name = kwargs['bucket']
#         key = kwargs['key']
#         local_path = f'<path>/temp-{timestamp_str}-{random_uuid}.csv'
#         s3.download_file(bucket_name, key, local_path)

#         # loader = CustomCSVLoader(file_path=local_path, row_count=1)
#         # loader = CustomCSVLoader(file_path=local_path, row_count=999)
#         loader = CustomCSVLoader(file_path=local_path, row_count=2)
#         # loader = CustomCSVLoader(file_path=local_path, row_count=3)
#         data = loader.load()
#         # print(data)

#     # TSV
#     # process_csv("x", {'bucket': '<bucket_name>', 'key': 'athena_results/OrderTable.tsv'})
#     # CSV
#     process_csv("x", {'bucket': '<bucket_name>', 'key': 'athena_results/sdps-api-test-s3-key-58h54muj.csv'})
