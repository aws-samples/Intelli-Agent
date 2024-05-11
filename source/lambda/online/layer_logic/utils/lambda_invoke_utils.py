from langchain.pydantic_v1 import BaseModel,root_validator,Field
from typing import Any,Optional,Dict
import json 
import importlib
from .exceptions import LambdaInvokeError
import functools 
import os 
<<<<<<< HEAD
import boto3


class LambdaInvoker(BaseModel):
    # aws lambda clinet
    client: Any = None 
    # use the following envs for boto3 lambda client
    region_name: str = os.environ.get("AWS_REGION","")
    credentials_profile_name: Optional[str] = os.environ.get("AWS_PROFILE","default")
=======
import boto3 
import requests 
import enum 

class LAMBDA_INVOKE_MODE(enum.Enum):
    LAMBDA = 'lambda'
    LOCAL = "local"
    APIGETAWAY = "apigetaway"
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_ 
    
    @classmethod
    def values(cls):
        return [e.value for e in cls]
    
class LambdaInvoker(BaseModel):
    # aws lambda clinet
    client: Any = None 
    region_name: str = None
    credentials_profile_name: Optional[str] = Field(default=None, exclude=True)
>>>>>>> 27289d7362c6309c35017ab03483d710a00b3e7a

    @root_validator()
    def validate_environment(cls, values: Dict):
        if values.get("client") is not None:
            return values

        try:
            import boto3
            try:
                if values["credentials_profile_name"] is not None:
                    session = boto3.Session(
                        profile_name=values["credentials_profile_name"]
                    )
                else:
                    # use default credentials
                    session = boto3.Session()

                values["client"] = session.client(
                    "lambda", region_name=values["region_name"]
                )

            except Exception as e:
                raise ValueError(
                    "Could not load credentials to authenticate with AWS client. "
                    "Please check that credentials in the specified "
                    f"profile name are valid. {e}"
                ) from e

        except ImportError:
            raise ImportError(
                "Could not import boto3 python package. "
                "Please install it with `pip install boto3`."
            )
        return values

    def invoke_with_lambda(self,lambda_name:str,event_body:dict):
        invoke_response = self.client.invoke(FunctionName=lambda_name,
                                           InvocationType='RequestResponse',
                                           Payload=json.dumps(event_body))
        response_body = invoke_response['Payload']
        response_body = json.loads(response_body.read().decode("unicode_escape"))

        if "errorType" in response_body:
            error = f"{lambda_name} invoke failed\n\n" + "\n".join(response_body['stackTrace']) + "\n" + f"{response_body['errorType']}: {response_body['errorMessage']}"
            raise LambdaInvokeError(error)
        
        return response_body

    def invoke_with_local(self,lambda_module_path:str,event_body:dict,handler_name="lambda_handler"):
        lambda_module = importlib.import_module(lambda_module_path)
        ret = getattr(lambda_module,handler_name)(event_body)
        return ret 

    
    def invoke_with_apigateway(self,url,event_body:dict):
        r = requests.post(url,json=event_body)
        data = r.json()
        if r.status_code != 200:
            raise LambdaInvokeError(str(data))

        ret = json.loads(data['body'])
        return ret 

<<<<<<< HEAD
obj = LambdaInvoker(client=boto3.client("lambda"))
invoke_with_handler = obj.invoke_with_handler
invoke_with_lambda = obj.invoke_with_lambda
=======

    def invoke_lambda(
            self,
            event_body,
            lambda_invoke_mode: LAMBDA_INVOKE_MODE = "local",
            lambda_name=None,
            lambda_module_path=None,
            handler_name=None,
            apigetway_url=None
        ):
        assert LAMBDA_INVOKE_MODE.has_value(lambda_invoke_mode), (lambda_invoke_mode,LAMBDA_INVOKE_MODE.values())

        if lambda_invoke_mode == LAMBDA_INVOKE_MODE.LAMBDA.value:
            return self.invoke_with_remote(lambda_name=lambda_name,event_body=event_body)
        elif lambda_invoke_mode == LAMBDA_INVOKE_MODE.LOCAL.value:
            return self.invoke_with_local(
                lambda_module_path=lambda_module_path,
                event_body=event_body,
                handler_name=handler_name
                )
        elif lambda_invoke_mode == LAMBDA_INVOKE_MODE.APIGETAWAY.value:
            return self.invoke_with_apigetaway(
                url=apigetway_url,
                event_body=event_body
            )

obj = LambdaInvoker()
invoke_with_local = obj.invoke_with_local
invoke_with_remote = obj.invoke_with_lambda
invoke_with_apigateway = obj.invoke_with_apigateway
invoke_lambda = obj.invoke_lambda


def chatbot_lambda_call_wrapper(fn):
    @functools.wraps(fn)
    def inner(event:dict,context=None):
        # 处理chat history 序列化的问题
        if "lambda_invoke_mode" not in event:
            event['lambda_invoke_mode'] = os.environ.get("LAMBDA_INVOKE_MODE","local")
         
        ret = fn(event,context=context)
        # 如果使用apigateway 调用lambda，需要将结果保存到body字段中
        if event['lambda_invoke_mode'] == LAMBDA_INVOKE_MODE.APIGETAWAY.value:
            ret = {
                "isBase64Encoded": False,
                "statusCode": 200,
                "body": json.dumps(ret),
                "headers": {
                    "content-type": "application/json"
                }
            }

        return ret 
    return inner 
>>>>>>> 27289d7362c6309c35017ab03483d710a00b3e7a





        
