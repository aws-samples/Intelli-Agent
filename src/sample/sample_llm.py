import logging
from embedding_wrapper import CSDCEmbeddings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if __name__ == "__main__":
    embeddings = CSDCEmbeddings(
        aosEndpointName = 'vpc-xx.us-east-1.es.amazonaws.com',
        region = 'us-east-1'
    )
    doc_reult = embeddings.embed_documents(
        bucketName='llm-bot-documents-xx-us-east-1',
        prefix='csdc'
    )
    query_result = embeddings.embed_query(
        text="请给我介绍一下什么是Data Transfer Hub方案？"
    )
    logging.info(f"doc_reult is {doc_reult}, the type of doc_reult is {type(doc_reult)}, query_result is {query_result}, the type of query_result is {type(query_result)}")
