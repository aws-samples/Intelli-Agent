from langchain.pydantic_v1 import BaseModel,root_validator,Field
from typing import Any,Optional,Dict
import json 
import os
import boto3 
import time 
import importlib
from .exceptions import LambdaInvokeError
import functools 
import requests 
import enum 
from common_utils.logger_utils import get_logger
from common_utils.serialization_utils import JSONEncoder
from common_utils.websocket_utils import is_websocket_request,send_to_ws_client
from common_utils.constant import StreamMessageType

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
_is_current_invoke_local = False
_current_stream_use = True
_ws_connection_id = None 
    
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
            handler_name="lambda_handler",
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
        global _lambda_invoke_mode, _is_current_invoke_local
        _is_current_invoke_local = True if context is None else False
        current_lambda_invoke_mode = LAMBDA_INVOKE_MODE.LOCAL.value
        # avoid recursive lambda calling
        if context is not None and type(context).__name__ == "LambdaContext":
            context = context.__dict__ 
            _lambda_invoke_mode = LAMBDA_INVOKE_MODE.LOCAL.value
            # logger.info(f'event: {json.dumps(event,ensure_ascii=False,indent=2,cls=JSONEncoder)}')
        
        if "Records" in event:
            records = event["Records"]
            assert len(records),"Please set sqs batch size to 1"
            event = json.loads(records[0]['body'])
            _lambda_invoke_mode = LAMBDA_INVOKE_MODE.LOCAL.value
            current_lambda_invoke_mode = LAMBDA_INVOKE_MODE.APIGETAWAY.value
        
        context = context or {}
        context['request_timestamp'] = time.time()
        stream:bool = is_websocket_request(event)
        context['stream'] = stream
        if stream:
            ws_connection_id = event["requestContext"]["connectionId"]
            context['ws_connection_id'] = ws_connection_id
        
        # apigateway wrap event into body
        if "body" in event:
            _lambda_invoke_mode = LAMBDA_INVOKE_MODE.LOCAL.value
            current_lambda_invoke_mode = LAMBDA_INVOKE_MODE.APIGETAWAY.value
            event = json.loads(event["body"])
        ret = fn(event, context=context)
        # save response to body
        # TODO
        if current_lambda_invoke_mode  == LAMBDA_INVOKE_MODE.APIGETAWAY.value:
            ret = {
                "statusCode": 200,
                "body": json.dumps(ret),
                "headers": {
                    "content-type": "application/json"
                }
            }

        return ret 
    return inner 


def is_running_local():
    return _is_current_invoke_local


def send_trace(trace_info:str):
    if _current_stream_use and _ws_connection_id is not None:
        send_to_ws_client(
            message={
                    "message_type":StreamMessageType.MONITOR,
                    "message":trace_info,
                    "created_time": time.time()
                    },
            ws_connection_id=_ws_connection_id
        )
    else:
        logger.info(trace_info)


def node_monitor_wrapper(fn=None,*, monitor_key="current_monitor_infos"):
    def inner(fn):
        @functools.wraps(fn)
        def inner2(state:dict):
            enter_time = time.time()
            send_trace(f"\n\n")
            send_trace(f"\n\n **Enter {fn.__name__}**, time: {enter_time}")
            global _current_stream_use,_ws_connection_id
            _current_stream_use = state['stream']
            _ws_connection_id = state['ws_connection_id']
            output = fn(state)
            current_monitor_infos = output.get(monitor_key,None)
            if current_monitor_infos is not None:
                # sent to wwebsocket
                send_trace(f"\n\n {current_monitor_infos}")
            exit_time = time.time()
            send_trace(f"\n\n **Exit {fn.__name__}**, time: {exit_time}, elapsed time: {exit_time-enter_time}s")
            return output
        return inner2 
    if fn is not None:
        assert callable(fn),fn
    if callable(fn):
        return inner(fn)
    return inner






        
