from langchain.pydantic_v1 import BaseModel,root_validator,Field
from typing import Any,Optional,Dict
import json 
import importlib
from .exceptions import LambdaInvokeError
import functools 
import requests 
import enum 
from common_utils.logger_utils import get_logger
from common_utils.serialization_utils import JSONEncoder

logger = get_logger("lambda_invoke_utils")

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

_lambda_invoke_mode = LAMBDA_INVOKE_MODE.LOCAL.value
    
class LambdaInvoker(BaseModel):
    # aws lambda clinet
    client: Any = None 
    region_name: str = None
    credentials_profile_name: Optional[str] = Field(default=None, exclude=True)

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
        response_str = response_body.read().decode()

        response_body = json.loads(response_str)

        if "errorType" in response_body:
            error = f"{lambda_name} invoke failed\n\n" + "".join(response_body['stackTrace']) + "\n" + f"{response_body['errorType']}: {response_body['errorMessage']}"
            raise LambdaInvokeError(error)
        
        return response_body

    def invoke_with_local(self,
                          lambda_module_path:str,
                          event_body:dict,
                          handler_name="lambda_handler"):
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

    def invoke_lambda(
            self,
            event_body,
            lambda_invoke_mode: LAMBDA_INVOKE_MODE = None,
            lambda_name=None,
            lambda_module_path=None,
            handler_name=None,
            apigetway_url=None
        ):
        lambda_invoke_mode = lambda_invoke_mode or _lambda_invoke_mode

        assert LAMBDA_INVOKE_MODE.has_value(lambda_invoke_mode), (lambda_invoke_mode,LAMBDA_INVOKE_MODE.values())

        if lambda_invoke_mode == LAMBDA_INVOKE_MODE.LAMBDA.value:
            return self.invoke_with_lambda(lambda_name=lambda_name,event_body=event_body)
        elif lambda_invoke_mode == LAMBDA_INVOKE_MODE.LOCAL.value:
            return self.invoke_with_local(
                lambda_module_path=lambda_module_path,
                event_body=event_body,
                handler_name=handler_name
                )
        elif lambda_invoke_mode == LAMBDA_INVOKE_MODE.APIGETAWAY.value:
            return self.invoke_with_apigateway(
                url=apigetway_url,
                event_body=event_body
            )

obj = LambdaInvoker()
invoke_with_local = obj.invoke_with_local
invoke_with_lambda = obj.invoke_with_lambda
invoke_with_apigateway = obj.invoke_with_apigateway
invoke_lambda = obj.invoke_lambda


def chatbot_lambda_call_wrapper(fn):
    @functools.wraps(fn)
    def inner(event:dict,context=None):
        global _lambda_invoke_mode
        # avoid recursive lambda calling
        if str(type(context)) == "LambdaContext":
            _lambda_invoke_mode = LAMBDA_INVOKE_MODE.LOCAL.value
            logger.info(f'event: {json.dumps(event,ensure_ascii=False,indent=2,cls=JSONEncoder)}')

        # if "lambda_invoke_mode" not in event:
        #     event['lambda_invoke_mode'] = os.environ.get("LAMBDA_INVOKE_MODE","local")
        
        
        base_state = {
            "message_id":"",
            "trace_infos": []
        }
        
        ret = fn({**base_state,**event}, context=context)
        # 如果使用apigateway 调用lambda，需要将结果保存到body字段中
        # TODO
        if _lambda_invoke_mode  == LAMBDA_INVOKE_MODE.APIGETAWAY.value:
            ret = {
                # "isBase64Encoded": False,
                "statusCode": 200,
                "body": json.dumps(ret),
                "headers": {
                    "content-type": "application/json"
                }
            }

        return ret 
    return inner 





        
