import os
import boto3
import json
from tenacity import retry, stop_after_attempt
from typing import List

from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

from langchain.docstore.document import Document
from langchain.vectorstores import OpenSearchVectorSearch

from sm_utils import create_sagemaker_embeddings_from_js_model

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

credentials = boto3.Session().get_credentials()
region = boto3.Session().region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

# Get params from Lambda environment variables
aosEndpoint = os.environ.get('opensearch_cluster_domain')
embeddingModelEndpoint = os.environ.get('embedding_endpoint')

class OpenSearchClient:
    def __init__(self, _opensearch_cluster_domain: str):
        """
        Initialize OpenSearch client using OpenSearch Endpoint
        """
        self.client = OpenSearch(
            hosts = [{'host': _opensearch_cluster_domain.replace("https://", ""), 'port': 443}],
            http_auth = awsauth,
            use_ssl = True,
            verify_certs = True,
            connection_class = RequestsHttpConnection,
            region=region
        )

    def create_index(self, index: str, body: str, _kwargs: dict):
        """
        Create an index in OpenSearch.

        Args:
            index (str): The name of the index to create.
            body (dict): A dictionary containing the settings and mappings for the index.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "create",
            "body": {
                "settings": {
                "index": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1
                }
                },
                "mappings": {
                "properties": {
                    "vector_field": {
                        "type": "knn_vector",
                        "dimension": 1024
                    }
                }
                }
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} already exist'})
            }
        body_dict = json.loads(body)
        # fixed settings and mappings
        body = {
            "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
            "mappings": {
                "properties": {
                    "vector_field": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "nmslib",
                            "parameters": {"ef_construction": 512, "m": 16},
                        },
                    }
                }
            },
        }
        # Create the index with the specified settings and mappings
        response = self.client.indices.create(index=index, body=body)
        return response

    def query_index(self, index: str, body: str, _kwargs: dict):
        """
        Get all mappings for specified index or indices.
        :param index_name: Name of the index or '_all' for all indices.
        :return: Mappings of the index or indices.
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        # set default index to '_all' if index is not specified
        if index == '':
            index = '_all'
        return self.client.indices.get_mapping(index=index)

    def delete_index(self, index: str, _body: str, _kwargs: dict):
        """
        Delete an index in OpenSearch.

        Args:
            index (str): The name of the index to delete.
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        
        # delete the index
        response = self.client.indices.delete(index=index)
        return response

    def delete_document(self, index: str, body: str, _kwargs: dict):
        """
        Delete a document in a specific index.

        Args:
            index (str): The name of the index to delete.
            document_id (str): The id of the document to delete.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "delete_document",
            "body": {
                "document_id": "1"
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        document_id = body_dict.get('body', {}).get('document_id', {})
        # delete the document
        self.client.delete(index=index, id=document_id)

    def bulk(self, index: str, body: str, _kwargs: dict):
        """
        Bulk index documents in a specific index.

        Args:
            index (str): The name of the index to delete.
            document (List[Document]): A list of documents to index.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "bulk",
            "body": {
                List[Document]
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        document = body_dict.get('body', {})
        # bulk index the documents
        self.client.bulk(index=index, body=document)

    def index(self, index: str, body: str, _kwargs: dict):
        """
        Index a document in a specific index.

        Args:
            index (str): The name of the index to delete.
            document (List[Document]): A list of documents to index.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "index",
            "body": {
                List[Document]
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        document = body_dict.get('body', {})
        # iterate through the documents and index them
        for doc in document:
            try:
                response = self.client.index(index=index, body=doc)
                logger.info(f"response: {response}")
            except Exception as e:
                logger.error(f"Error indexing document: {e}")

    def query_all(self, index: str, _body: str, _kwargs: dict):
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body = {
            "query": {
                "match_all": {}
            }
        }
        response = self.client.search(index=index, body=body)
        return response

    def query_full_text_match(self, index: str, body: str, _kwargs: dict):
        """
        Basic query with fixed result size

        Args:
            index (str): The name of the index to delete.
            body (str): The query body.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "query",
            "body": {
                "field": field,
                "value": value,
                "size": size
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        field = str(body_dict.get('field'))
        value = str(body_dict.get('value'))
        # optional size with default value 100
        size = str(body_dict.get('size', 100))
        logger.info(f"field: {field}, value: {value}, size: {size}")
        body = {
            "query": {
                # use term-level queries only for fields mapped as keyword
                "match": {
                    field: value
                    # "operator": "and",
                    # "minimum_should_match": 2
                }
            },
            "size": size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                }
            ]
        }
        response = self.client.search(index=index, body=body)
        return response

    def query_full_text_multi_match(self, index: str, body: str, _kwargs: dict):
        """
        Basic query with fixed result size

        Args:
            index (str): The name of the index to delete.
            body (str): The query body.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "query",
            "body": {
                "field": field,
                "value": value,
                "size": size
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        field = str(body_dict.get('field'))
        value = str(body_dict.get('value'))
        # optional size with default value 100
        size = str(body_dict.get('size', 100))
        logger.info(f"field: {field}, value: {value}, size: {size}")
        body = {
            "query": {
                # use term-level queries only for fields mapped as keyword
                "multi_match": {
                    "query": field,
                    # sample: "fields": ["title", "body"]
                    "fields": value,
                    "type": "best_fields",
                    # add (tie_breaker * _score) for all other matching fields
                    # "tie_breaker": 0.3
                }
            },
            "size": size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                }
            ]
        }
        response = self.client.search(index=index, body=body)
        return response

    def query_term(self, index: str, body: str, _kwargs: dict):
        """
        Execute a term-level query, documents returned by a term-level query are not sorted by their relevance scores.

        Args:
            index (str): The name of the index to delete.
            body (str): The query body.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "query_term",
            "body": {
                "quey": query,
                "filter": filter
                "size": size
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        field = str(body_dict.get('field'))
        value = str(body_dict.get('value'))
        # optional size with default value 100
        size = str(body_dict.get('size', 100))
        logger.info(f"field: {field}, value: {value}, size: {size}")
        # With a filter context, OpenSearch returns matching documents without calculating a relevance score.
        body = {
            "query": {
                # use term-level queries only for fields mapped as keyword
                "term": {
                    field:{
                        "value": value,
                        "case_insensitive": false
                    }
                }
            },
            "size": size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                }
            ]
        }
        response = self.client.search(index=index, body=body)
        return response

    def query_term_regex(self, index: str, body: str, _kwargs: dict):
        """
        Execute a term-level query, documents returned by a term-level query are not sorted by their relevance scores.

        Args:
            index (str): The name of the index to delete.
            body (str): The query body.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "query_term",
            "body": {
                "quey": query,
                "filter": filter
                "size": size
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        field = str(body_dict.get('field'))
        value = str(body_dict.get('value'))
        # optional size with default value 100
        size = str(body_dict.get('size', 100))
        logger.info(f"field: {field}, value: {value}, size: {size}")
        # With a filter context, OpenSearch returns matching documents without calculating a relevance score.
        body = {
            "query": {
                # use term-level queries only for fields mapped as keyword
                "regexp": {
                    field:{
                        "value": value,
                        "case_insensitive": false
                    }
                }
            },
            "size": size,
            "sort": [
                {
                    "_score": {
                        "order": "desc"
                    }
                }
            ]
        }
        response = self.client.search(index=index, body=body)
        return response

    def query_knn(self, index: str, body: str, _kwargs: dict):
        """
        Execute a search query using knn.

        Args:
            index (str): The name of the index to delete.
            body (str): The query body.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "query_knn",
            "body": {
                "query": query,
                "field": field,
                "size": size
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        query = body_dict.get('query')
        # optional size with default value 100
        size = str(body_dict.get('size', 100))
        logging.info(f"query: {query}, size: {size}")
        body = {
            "size": size,
            "query": {
                "knn": {
                    "vector_field": {
                        "vector": query,
                        "k": size
                    }
                }
            }
        }
        response = self.client.search(index=index, body=body)
        return response

    def query_exact(self, index: str, body: str, _kwargs: dict):
        """
        Execute a search query using exact match.

        Args:
            index (str): The name of the index to delete.
            body (str): The query body.

        Sample body:
        {
            "aos_index": "chatbot-index",
            "operation": "query_exact",
            "body": {
                "query": query,
                "field": field,
                "size": size
            }
        }
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body_dict = json.loads(body)
        query = str(body_dict.get('query'))
        field = str(body_dict.get('field'))
        # optional size with default value 100
        size = str(body_dict.get('size', 100))
        body =  {
            "query" : {
                "match_phrase":{
                    field : query
                }
            }
        }
        response = self.client.search(index=index, body=body)
        return response

    # @retry(stop=stop_after_attempt(3))
    def _embed_document(self, index: str, document: Document, _kwargs: dict):
        embeddings = create_sagemaker_embeddings_from_js_model(embeddingModelEndpoint, region)
        docsearch = OpenSearchVectorSearch(
            index_name=index,
            embedding_function=embeddings,
            opensearch_url="https://{}".format(aosEndpoint),
            http_auth = awsauth,
            use_ssl = True,
            verify_certs = True,
            connection_class = RequestsHttpConnection
        )
        logger.info("Adding documents %s to OpenSearch with index %s", document, index)
        # List of ids from adding the texts into the vectorstore.
        return docsearch.add_documents(documents=[document])
        # logger.info("Retry statistics: %s", _embed_document.retry.statistics)

    def embed_document(self, index: str, body: str, _kwargs: dict):
        """
        Returns:
            List of ids from adding the texts into the vectorstore.

        Sample body:
        {
            "index": "chatbot-index",
            "operation": "embed_document",
            "body": {
                "documents": {
                    "page_content": "This is a test",
                    "metadata": {
                        "heading_hierarchy": "Title 1"
                        ...
                    }
                }
            }
        }
        """
        body_dict = json.loads(body)
        # assemble the document according to the Document class below:      
        document = Document(
            page_content=body_dict['documents']['page_content'],
            metadata=body_dict['documents']['metadata']
        )
        # if the embedding function execute successfully, return success with the document id
        res = self._embed_document(index, document, _kwargs)
        # assemble the response
        response = {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': {'document_id': res}
        }
        return response