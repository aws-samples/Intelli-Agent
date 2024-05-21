import json
import logging
import os
from urllib.request import urlopen

import jwt
import requests

# Replace with your Cognito User Pool info
USER_POOL_ID = os.environ["USER_POOL_ID"]
REGION = os.environ["REGION"]
APP_CLIENT_ID = os.environ["APP_CLIENT_ID"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)

keys_url = "https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json".format(
    REGION, USER_POOL_ID
)

response = urlopen(keys_url)
keys = json.loads(response.read())["keys"]


def lambda_handler(event, context):
    logger.info(event)
    # token = event["authorizationToken"]
    # headers = jwt.get_unverified_header(token)
    # kid = headers["kid"]

    # # Search for the kid in the downloaded public keys
    # key_index = -1
    # for i in range(len(keys)):
    #     if kid == keys[i]["kid"]:
    #         key_index = i
    #         break
    # if key_index == -1:
    #     print("Public key not found in jwks.json")
    #     return None

    # # Construct the public key
    # public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(keys[key_index]))

    # # Verify the signature of the JWT token
    # claims = jwt.decode(token, public_key, algorithms=["RS256"], audience=APP_CLIENT_ID)

    # # Verify the token issuer
    # if claims["iss"] != "https://cognito-idp.{}.amazonaws.com/{}".format(
    #     REGION, USER_POOL_ID
    # ):
    #     print("Token was not issued by the correct issuer")
    #     return None

    # # Verify the token client
    # if claims["aud"] != APP_CLIENT_ID:
    #     print("Token was not issued for this audience")
    #     return None

    return {"custom_response": True}

    # return claims
