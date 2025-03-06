import json

import boto3

logger = logging.getLogger(__name__)

secrets_client = boto3.client("secretsmanager")


def get_api_key(api_secret_name):
    """
    Get the API key from AWS Secrets Manager.
    Args:
        api_secret_name (str): The name of the secret in AWS Secrets Manager containing the API key.
    Returns:
        str: The API key.
    """
    try:
        secret_response = secrets_client.get_secret_value(
            SecretId=api_secret_name
        )
        if "SecretString" in secret_response:
            secret_data = json.loads(secret_response["SecretString"])
            api_key = secret_data.get("api_key")
            logger.info(
                f"Successfully retrieved API key from secret: {api_secret_name}"
            )
            return api_key
    except Exception as e:
        logger.error(f"Error retrieving secret {api_secret_name}: {str(e)}")
        raise
    return None
