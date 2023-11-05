import boto3
import json
from typing import List

from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

credentials = boto3.Session().get_credentials()
region = boto3.Session().region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

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
    def create_index(self, index: str, body: str):
        """
        Create an index in OpenSearch.

        Args:
            index (str): The name of the index to create.
            body (dict): A dictionary containing the settings and mappings for the index.
        """
        body_dict = json.loads(body)
        # Extract the settings and mappings from the body
        settings = body_dict.get('body', {}).get('settings', {})
        mappings = body_dict.get('body', {}).get('mappings', {})

        # Create the index with the specified settings and mappings
        self.client.indices.create(
            index=index,
            body={
                'settings': settings,
                'mappings': mappings
            }
        )

    def delete_index(self, index: str):
        """
        Delete an index in OpenSearch.
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            # hint to the caller that the index does not exist
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        # delete the index
        self.client.indices.delete(index=index)
    def delete_document(self, index: str, document_id: str):
        """
        Delete a document in a specific index.
        """
        # delete the document
        self.client.delete(index=index, id=document_id)
    def bulk(self, index: str, document: List[str]):
        """
        Bulk index documents in a specific index.
        """
        # bulk index the documents
        self.client.bulk(index=index, body=document)
    def index(self, index: str, document: List[str]):
        """
        Index a document in a specific index.
        """
        # iterate through the documents and index them
        for doc in document:
            try:
                response = self.client.index(index=index, body=doc)
                logger.info(f"response: {response}")
            except Exception as e:
                logger.error(f"Error indexing document: {e}")
    def query(self, index: str, field: str, value: str):
        """
        Execute a query on a specific index based on a field and value.
        """
        body = {
            "query": {
                "match": {
                    field: value
                }
            }
        }
        response = self.client.search(index=index, body=body)
        return response
    def match_all(self, index: str):
        """
        Execute a match_all query on a specific index.
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            # hint to the caller that the index does not exist
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
    def search_with_metadata(self, index: str, query: str, filter: str):
        """
        Execute a search query using the query DSL, using bool query to filter on metadata.
        """
        # avoid NotFoundError: NotFoundError(404, 'index_not_found_exception'...
        if not self.client.indices.exists(index=index):
            # hint to the caller that the index does not exist
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'index {index} does not exist'})
            }
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"content": query}},
                    ],
                    # looking for documents where the metadata field exactly matches the value of filter
                    "filter": [
                        {"term": {"metadata": filter}}
                    ]
                }
            }
        }
        response = self.client.search(index=index, body=body)
        return response