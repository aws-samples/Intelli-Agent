import json
import logging
import os

import boto3

logger = logging.getLogger()
# logging.basicConfig(format='%(asctime)s,%(module)s,%(processName)s,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stderr)
logger.setLevel(logging.INFO)

# fetch all the environment variables
_opensearch_cluster_domain = os.environ.get("opensearch_cluster_domain")
_opensearch_region = os.environ.get("embedding_endpoint")
_jobName = os.environ.get("jobName")
_jobQueueArn = os.environ.get("jobQueueArn")
_jobDefinitionArn = os.environ.get("jobDefinitionArn")

batch_client = boto3.client("batch")


def lambda_handler(event, _context):
    logger.info("Received event: " + json.dumps(event, indent=2))

    try:
        response = batch_client.submit_job(
            jobName=_jobName,
            jobQueue=_jobQueueArn,
            jobDefinition=_jobDefinitionArn,
            containerOverrides={
                "environment": [
                    {
                        "name": "opensearch_cluster_domain",
                        "value": _opensearch_cluster_domain,
                    },
                    {"name": "opensearch_region", "value": _opensearch_region},
                ]
            },
        )
        return {
            "statusCode": 200,
            "body": json.dumps("Batch job submitted: " + response["jobId"]),
        }
    except Exception as e:
        logger.error(e)
        raise e
