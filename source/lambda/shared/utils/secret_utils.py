import boto3
from botocore.exceptions import ClientError


session = boto3.session.Session()
secret_manager_client = session.client(
    service_name="secretsmanager"
)



def get_secret_value(secret_arn: str):
    """Get secret value from secret manager

    Args:
        secret_arn (str): secret arn

    Returns:
        str: secret value
    """
    try:
        get_secret_value_response = secret_manager_client.get_secret_value(
            SecretId=secret_arn
        )
    except ClientError as e:
        raise Exception("Fail to retrieve the secret value: {}".format(e))
    else:
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
            return secret
        else:
            raise Exception("Fail to retrieve the secret value")