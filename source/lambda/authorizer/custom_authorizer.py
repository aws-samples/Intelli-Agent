import json
import logging
import os
import traceback
from urllib.request import urlopen

import jwt

# Replace with your Cognito User Pool info
REGION = os.environ["REGION"]
verify_exp = os.getenv("mode") != "dev"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# issuer = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
# keys_url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
# response = urlopen(keys_url)
# keys = json.loads(response.read())["keys"]


def generatePolicy(principalId, effect, resource, claims):
    authResponse = {}
    authResponse["principalId"] = principalId
    if effect and resource:
        policyDocument = {}
        policyDocument["Version"] = "2012-10-17"
        policyDocument["Statement"] = []
        statementOne = {}
        statementOne["Action"] = "execute-api:Invoke"
        statementOne["Effect"] = effect
        statementOne["Resource"] = resource
        policyDocument["Statement"] = [statementOne]
        authResponse["policyDocument"] = policyDocument
    authResponse["context"] = {
        "claims": json.dumps(claims),
        "authorizerType": "lambda_authorizer",
    }

    authResponse_JSON = json.dumps(authResponse)

    return authResponse_JSON


def generateAllow(principalId, resource, claims):
    return generatePolicy(principalId, "Allow", resource, claims)


def generateDeny(principalId, resource, claims):
    return generatePolicy(principalId, "Deny", resource, claims)


def lambda_handler(event, context):
    logger.info(event)
    try:
        if event.get("httpMethod"):
            # REST API
            if event["headers"].get("authorization"):
                # Browser will change the Authorization header to lowercase
                token = event["headers"]["authorization"].replace("Bearer", "").strip()
            else:
                # Postman
                token = event["headers"]["Authorization"].replace("Bearer", "").strip()
        else:
            # WebSocket API
            token = event["queryStringParameters"]["idToken"]

        headers = jwt.get_unverified_header(token)
        kid = headers["kid"]


        oidc_info = event["headers"].get("Oidc-Info")
        if oidc_info.provider == "authing":
            issuer = f"{oidc_info.redirectUri}/oidc"
            keys_url = f"{oidc_info.redirectUri}/oidc/.well-known/jwks.json"
        else:
            issuer = f"https://cognito-idp.{REGION}.amazonaws.com/{oidc_info.poolId}"
            keys_url = f"https://cognito-idp.{REGION}.amazonaws.com/{oidc_info.poolId}/.well-known/jwks.json"
        
        response = urlopen(keys_url)
        keys = json.loads(response.read())["keys"]

        # Search for the kid in the downloaded public keys
        key_index = -1
        for i, key in enumerate(keys):
            if kid == key["kid"]:
                key_index = i
                break
        if key_index == -1:
            logger.error("Public key not found in jwks.json")
            raise Exception(
                "Custom Authorizer Error: Public key not found in jwks.json"
            )
        # # Construct the public key
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(keys[key_index]))

        # Verify the signature of the JWT token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=oidc_info.clientId,
            issuer=issuer,
            options={"verify_exp": verify_exp},
        )
        # reformat claims to align with cognito output
        claims["cognito:groups"] = ",".join(claims["cognito:groups"])
        logger.info(claims)
        # # Verify the signature of the JWT token
        # claims = jwt.decode(
        #     token, public_key, algorithms=["RS256"], audience=APP_CLIENT_ID,
        #     issuer=issuer, options={"verify_exp": verify_exp}
        # )
        # # reformat claims to align with cognito output
        # claims["cognito:groups"] = ",".join(claims["cognito:groups"])
        # logger.info(claims)

        response = generateAllow("me", "*", claims)
        logger.info("Authorized")
        return json.loads(response)

    except Exception as e:
        logger.info("Not Authorized")
        msg = traceback.format_exc()
        logger.error(msg)
        claims = {}
        response = generateDeny("me", "*", claims)
        return json.loads(response)
