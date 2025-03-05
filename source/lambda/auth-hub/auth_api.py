import logging.config
import os
import boto3
from mangum import Mangum

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import jwt
# from openai import BaseModel
from pydantic import BaseModel
import requests
# from jwt.jwks_client import PyJWKClient
import yaml 

logger = logging.getLogger(__name__)

token_list = []
authApp = FastAPI()

with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

class LoginRequest(BaseModel):
    # 用户名
    username: str
    # 密码
    password: str
    # 提供者
    provider: str
    # 客户端ID
    client_id: str = ''
    # 重定向URI
    redirect_uri: str = ''
    # 语言
    lang: str = 'en-US'

class RefreshRequest(BaseModel):
    provider: str
    client_id: str
    refresh_token: str
    redirect_uri: str

class VerifyRequest(BaseModel):
    redirect_uri: str

authApp.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@authApp.get("/auth")
async def root():
    return {"message": "Welcome to Auth API!"}

@authApp.post("/auth/login")
async def login(request: LoginRequest):
    return __custom_oidc_login(request)

@authApp.get("/auth/token/verify")
async def verify_token_main(request: Request, vRequest: VerifyRequest):
    authorization_header = request.headers.get('Authorization')
    if not authorization_header:
        raise HTTPException(status_code=400, detail="Missing Authorization header")
    
    token = authorization_header.split()[1]  # Bearer token
    validate_access_token_url = f"{vRequest.redirect_uri}/api/v2/oidc/validate_token?access_token={token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.get(validate_access_token_url, headers=headers)
    if response.status_code == 200:
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*'
            },
            'body': response.json()
        }
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)

@authApp.post("/auth/token/refresh")
async def verify_token_main(request: RefreshRequest):
    client_config = __get_client_config(request.provider, request.client_id)
    
    payload = {
        "client_id": client_config["client_id"],
        "client_secret": client_config["client_secret"],
        "grant_type": "refresh_token",
        "refresh_token": request.refresh_token
    }

    authing_login_url = f"{request.redirect_uri}/oidc/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(authing_login_url, data=payload, headers=headers)
    # response = requests.post(authing_login_url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)

handler = Mangum(authApp)

def __custom_oidc_login(request: LoginRequest):
    client_config = __get_client_config(request.provider, request.client_id)
    payload = {
        "client_id": client_config["client_id"],
        "client_secret": client_config["client_secret"],
        "grant_type": "password",
        "username": request.username,
        "password": request.password
    }

    authing_login_url = f"{request.redirect_uri}/oidc/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded','x-authing-lang': request.lang}
    response = requests.post(authing_login_url, data=payload, headers=headers, timeout=100)
    # if response.status_code == 200:
    return __gen_response_with_status_code(response.status_code, response.body.json())
    # else:
        # raise HTTPException(status_code=response.status_code, detail=response.text)

def __gen_response_with_status_code(code: int, body):
    return {
            'statusCode': code,
            'headers': {
               'Content-Type': 'application/json',
               'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
               'Access-Control-Allow-Origin': '*',
               'Access-Control-Allow-Methods': '*'
            },
            'body': body
        }


def __verify_token(token:str, request: VerifyRequest):
    jwks_url = f"{request.redirect_uri}/oidc/.well-known/jwks.json"
    # jwk_client = PyJWKClient(jwks_url)
    jwk_client = jwks_url

    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=request.client_id,
            issuer=f"{request.redirect_uri}/oidc"
        )
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_token_buitin_cognito(client_id: str, username: str, password: str, region: str):
    client = boto3.client('cognito-idp', region_name=region)
    response = client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        },
        ClientId=client_id
    )
    return response

def __refresh_token(auth_info):
    tokens = {
        "access_token": None,
        "refresh_token": auth_info.tokens["refresh_token"],
        "expires_at": datetime.utcnow()
    }
    response = requests.post(
        auth_info.token_url,
        data={
            "grant_type": "refresh_token",
            "client_id": auth_info.client_id,
            "client_secret": auth_info.client_secret,
            "refresh_token": auth_info.tokens["refresh_token"]
        }
    )
    if response.status_code == 200:
        token_data = response.json()
        tokens["access_token"] = token_data["access_token"]
        tokens["refresh_token"] = token_data.get("refresh_token", auth_info.tokens["refresh_token"])
        tokens["expires_at"] = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
    else:
        raise HTTPException(status_code=401, detail="Failed to refresh token")

def __get_client_config(provider: str, client_id: str):
    provider_config = config['oidc_providers'].get(provider)
    if not provider_config:
        raise HTTPException(status_code=400, detail="Invalid OIDC provider")

    client_config = next(
        (client for client in provider_config['clients'] if client['client_id'] == client_id), 
        None
    )
    if not client_config:
        raise HTTPException(status_code=400, detail="Invalid client id for provider")

    return client_config


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(authApp, host="127.0.0.1", port=3998)