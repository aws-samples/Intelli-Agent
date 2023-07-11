import json
import requests
from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from requests_aws4auth import AWS4Auth

credentials = boto3.Session().get_credentials()
region = boto3.Session().region_name
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)


QA_SEP = "=>"

def search_using_aos_knn(q_embedding, hostname, index, size=10):
    headers = {"Content-Type": "application/json"}

    #Note: 查询时无需指定排序方式，最临近的向量分数越高，做过归一化(0.0~1.0)
    query = {
        "size": size,
        "query": {
            "knn": {
                "embedding": {
                    "vector": q_embedding,
                    "k": size
                }
            }
        }
    }
    opensearch_knn_respose = []
    try:
        r = requests.post("https://"+hostname + "/" + index +
                        '/_search', headers=headers, json=query)
        results = json.loads(r.text)["hits"]["hits"]
        for item in results:
            opensearch_knn_respose.append( {'doc':"{}{}{}".format(item['_source']['doc'], QA_SEP, item['_source']['answer']),"doc_type":item["_source"]["doc_type"],"score":item["_score"]} )
        return opensearch_knn_respose
    except Exception as e:
        print(f'knn query exception:{str(e)}')
        return []
    


def aos_search(host, index_name, field, query_term, exactly_match=False, size=10):
    """
    search opensearch with query.
    :param host: AOS endpoint
    :param index_name: Target Index Name
    :param field: search field
    :param query_term: query term
    :return: aos response json
    """
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    query = None
    if exactly_match:
        query =  {
            "query" : {
                "match_phrase":{
                    "doc": query_term
                }
            }
        }
    else:
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
    query_response = client.search(
        body=query,
        index=index_name
    )

    if exactly_match:
        result_arr = [ {'doc': item['_source']['answer'], 'doc_type': 'A', 'score': item['_score']} for item in query_response["hits"]["hits"]]
    else:
        result_arr = [ {'doc':"{}{}{}".format(item['_source']['doc'], QA_SEP, item['_source']['answer']), 'doc_type': item['_source']['doc_type'], 'score': item['_score']} for item in query_response["hits"]["hits"]]

    return result_arr