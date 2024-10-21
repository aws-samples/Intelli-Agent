import json
import logging
import os

import boto3

cognito = boto3.client("cognito-idp")

cognito_user_pool_id = os.environ.get("USER_POOL_ID")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    authorizer_type = (
        event["requestContext"].get("authorizer", {}).get("authorizerType")
    )
    if authorizer_type == "lambda_authorizer":
        claims = json.loads(event["requestContext"]["authorizer"]["claims"])
        cognito_groups = claims["cognito:groups"]
        cognito_groups_list = cognito_groups.split(",")
    else:
        cognito_groups_list = ["Admin"]

    output = {}

    if "Admin" in cognito_groups_list:
        # Return a list of all cognito groups
        response = cognito.list_groups(UserPoolId=cognito_user_pool_id)
        output["chatbot_ids"] = [group["GroupName"] for group in response["Groups"]]
    else:
        output["chatbot_ids"] = cognito_groups_list
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
