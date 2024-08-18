import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_client = boto3.client("s3")
s3_bucket_name = os.environ.get("S3_BUCKET")


def create_presigned_url(bucket_name, object_name, content_type, expiration):
    """Generate a presigned URL to put a file to S3 bucket

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": bucket_name, "Key": object_name, "ContentType": content_type},
        ExpiresIn=expiration,
        HttpMethod="PUT",
    )

    return presigned_url


def lambda_handler(event, context):
    logger.info(event)
    authorizer_type = (
        event["requestContext"].get("authorizer", {}).get("authorizerType")
    )
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        cognito_groups = claims["cognito:groups"]
        cognito_groups_list = cognito_groups.split(",")
    else:
        cognito_groups_list = ["Admin"]
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }
    content_type = "text/plain;charset=UTF-8"
    expiration = 3600

    try:
        input_body = json.loads(event["body"])
        chatbot_id = (
            "Admin" if "Admin" in cognito_groups_list else cognito_groups_list[0]
        )
        file_name = "documents/" + chatbot_id + "/" + input_body["file_name"]
        if "content_type" in input_body:
            content_type = input_body["content_type"]
        if "expiration" in input_body:
            expiration = input_body["expiration"]

        presigned_url = create_presigned_url(
            s3_bucket_name, file_name, content_type, expiration
        )
        output = {
            "message": "The S3 presigned url is generated",
            "data": presigned_url,
            "s3Bucket": s3_bucket_name,
            "s3Prefix": file_name,
        }

        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(output),
        }
    except Exception as e:
        logger.error("Error: %s", str(e))

        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(e)}"),
        }
