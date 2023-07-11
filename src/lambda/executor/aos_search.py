import json
import boto3
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

credentials = boto3.Session().get_credentials()
region = boto3.Session().region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)


QA_SEP = "=>"

class OpenSearchClient:
    def __init__(self, host):
        """
        Initialize OpenSearch client using OpenSearch Endpoint
        """
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        self.query_match = {"knn": self._build_knn_search_query,
                            "exact": self._build_exactly_match_query,
                            "basic": self._build_basic_search_query}
    
    def _build_basic_search_query(self, index_name, query_term, field, size):
        """
        Build basic search query

        :param index_name: Target Index Name
        :param query_term: query term
        :param field: search field
        :param size: number of results to return from aos
        
        :return: aos response json
        """
        query = {
                "size": size,
                "query": {
                    "bool":{
                        "must":[ {"term": { "doc_type": "Q" }} ],
                        "should": [ {"match": { field : query_term }} ]
                    }
                },
                "sort": [
                    {
                        "_score": {
                            "order": "desc"
                        }
                    }
                ]
            }
        
        return query
    
    def _build_knn_search_query(self, index_name, query_term, field, size):
        """
        Build knn search query

        :param index_name: Target Index Name
        :param query_term: query term
        :param field: search field
        :param size: number of results to return from aos
        
        :return: aos response json
        """
        query = {
            "size": size,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_term,
                        "k": size
                    }
                }
            }
        }
        
        return query
    
    def _build_exactly_match_query(self, index_name, query_term, field, size):
        """
        Build exactly match query

        :param index_name: Target Index Name
        :param query_term: query term
        :param field: search field
        :param size: number of results to return from aos
        
        :return: aos response json
        """
        query =  {
            "query" : {
                "match_phrase":{
                    "doc": query_term
                }
            }
        }
        return query

    def organize_results(self, query_type, response):
        """
        Organize results from aos response

        :param query_type: query type
        :param response: aos response json
        """
        results = []
        aos_hits = response["hits"]["hits"]
        if query_type == "exact":
            for aos_hit in aos_hits:
                doc = aos_hit['_source']['answer']
                doc_type = "A"
                score = aos_hit["_score"]
                results.append({'doc': doc, 'doc_type': doc_type, 'score': score})
        else:
            for aos_hit in aos_hits:
                doc = f"{aos_hit['_source']['doc']}{QA_SEP}{aos_hit['_source']['answer']}"
                doc_type = aos_hit["_source"]["doc_type"]
                score = aos_hit["_score"]
                results.append({'doc': doc, 'doc_type': doc_type, 'score': score})
        return results

    def search(self, index_name, query_type, query_term, field: str = "doc", size: int = 10):
        """
        Perform search on aos
        
        :param index_name: Target Index Name
        :param query_type: query type
        :param query_term: query term
        :param field: search field
        :param size: number of results to return from aos
        
        :return: aos response json
        """
        query = self.query_match[query_type](index_name, query_term, field, size)
        response = self.client.search(
            body=query,
            index=index_name
        )
        result = self.organize_results(query_type, response)
        return result