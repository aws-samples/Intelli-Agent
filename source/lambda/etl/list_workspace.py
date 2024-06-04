import json
import logging
import os

import boto3

cognito = boto3.client("cognito-idp")

cognito_user_pool_id = os.environ.get("USER_POOL_ID")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info(event["requestContext"]["authorizer"]["claims"]["cognito:groups"])
    cognito_groups = event["requestContext"]["authorizer"]["claims"]["cognito:groups"]

    output = {}

    if cognito_groups == "Admin":
        # Return a list of all cognito groups
        response = cognito.list_groups(UserPoolId=cognito_user_pool_id)
        output["workspace_ids"] = [group["GroupName"] for group in response["Groups"]]
    else:
        output["workspace_ids"] = [cognito_groups]
    resp_header = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "*",
    }

    try:
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
