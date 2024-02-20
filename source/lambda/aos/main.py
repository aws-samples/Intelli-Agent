import json
import logging
import os

import boto3
from requests_aws4auth import AWS4Auth
from utils.aos_utils import OpenSearchClient

logger = logging.getLogger()
# logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)
logger.setLevel(logging.INFO)

# fetch all the environment variables
_opensearch_cluster_domain = os.environ.get("opensearch_cluster_domain")
_opensearch_region = os.environ.get("embedding_endpoint")


def lambda_handler(event, _context):
    logger.info("event: {}".format(event))
    # parse arguments from event
    index_name = json.loads(event["body"])["aos_index"]
    operation = json.loads(event["body"])["operation"]
    http_method = event["httpMethod"]
    body = json.loads(event["body"])["body"]
    aos_client = OpenSearchClient(_opensearch_cluster_domain)
    # other metadata need to pass to aos_client
    kwargs = json.loads(event["body"])

    operations_mapping = {
        "GET": {
            "query_all": lambda: aos_client.query_all(
                index_name, json.dumps(body), kwargs
            ),
            "query_full_text_match": lambda: aos_client.query_full_text_match(
                index_name, json.dumps(body), kwargs
            ),
            "query_full_text_multi_match": lambda: aos_client.query_full_text_multi_match(
                index_name, json.dumps(body), kwargs
            ),
            "query_term": lambda: aos_client.query_term(
                index_name, json.dumps(body), kwargs
            ),
            "query_term_regex": lambda: aos_client.query_term_wildcard(
                index_name, json.dumps(body), kwargs
            ),
            "query_knn": lambda: aos_client.query_knn(
                index_name, json.dumps(body), kwargs
            ),
            "query_exact": lambda: aos_client.query_exact(
                index_name, json.dumps(body), kwargs
            ),
            "query_index": lambda: aos_client.query_index(
                index_name, json.dumps(body), kwargs
            ),
        },
        "POST": {
            "create_index": lambda: aos_client.create_index(
                index_name, json.dumps(body), kwargs
            ),
            "update_index": lambda: aos_client.update_index(
                index_name, json.dumps(body), kwargs
            ),
            "index": lambda: aos_client.index(index_name, json.dumps(body), kwargs),
            "bulk": lambda: aos_client.bulk(index_name, json.dumps(body), kwargs),
            "delete_index": lambda: aos_client.delete_index(
                index_name, json.dumps(body), kwargs
            ),
            "delete_document": lambda: aos_client.delete_document(
                index_name, json.dumps(body), kwargs
            ),
            "embed_document": lambda: aos_client.embed_document(
                index_name, json.dumps(body), kwargs
            ),
            "embed_query": lambda: aos_client.embed_query(
                index_name, json.dumps(body), kwargs
            ),
        },
    }

    if (
        http_method in operations_mapping
        and operation in operations_mapping[http_method]
    ):
        response = operations_mapping[http_method][operation]()
        logger.info(
            "http_method: {}, operation: {}, response: {}".format(
                http_method, operation, response
            )
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response),
        }
    else:
        raise Exception(f"Invalid {http_method} operation: {operation}")
