
from pydantic import BaseModel,model_validator
from typing import Any,Optional,Dict
import json 
import importlib
import os 


class LambdaInvoker(BaseModel):
    # aws lambda clinet
    client: Any = None 
    region_name: str = os.environ.get("AWS_REGION","")
    credentials_profile_name: Optional[str] = os.environ.get("AWS_PROFILE","default")

    @model_validator(mode='before')
    @classmethod
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
        response_str = response_body.read().decode("unicode_escape")
        response_str = response_str.strip('"')
        
        return json.loads(response_str)

    def invoke_with_handler(self,lambda_module_path:str,event_body:dict,handler_name="lambda_handler"):
        lambda_module = importlib.import_module(lambda_module_path)
        ret = getattr(lambda_module,handler_name)(event_body)

        return ret 


obj = LambdaInvoker()
invoke_with_handler = obj.invoke_with_handler
invoke_with_lambda = obj.invoke_with_lambda





        
