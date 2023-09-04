import json
from abc import ABC
from typing import Any, Dict, List, Mapping, Optional

from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.llms.utils import enforce_stop_tokens
from langchain.pydantic_v1 import BaseModel, Extra, root_validator


class LLMInputOutputAdapter:
    """Adapter class to prepare the inputs from Langchain to a format
    that LLM model expects.

    It also provides helper function to extract
    the generated text from the model response."""

    @classmethod
    def prepare_input(
        cls, provider: str, prompt: str, model_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        input_body = {**model_kwargs}
        if provider == "CSDC":
            input_body = dict()
            input_body["inputs"] = prompt
            input_body["history"] = []
            input_body["parameters"] = {**model_kwargs}
        elif provider == "amazon":
            input_body = dict()
            input_body["inputText"] = prompt
            input_body["textGenerationConfig"] = {**model_kwargs}
        else:
            input_body["inputText"] = prompt

        return input_body

    @classmethod
    def prepare_output(cls, provider: str, response: Any) -> str:
        if provider == "CSDC":
            response_body = json.loads(response['Body'].read().decode("utf-8"))
            return response_body.get('outputs')
        else:
            response_body = json.loads(response.get("body").read())


class CSDCLLMBase(BaseModel, ABC):
    client: Any  #: :meta private:

    region_name: Optional[str] = None
    """The aws region e.g., `us-west-2`. Fallsback to AWS_DEFAULT_REGION env variable
    or region specified in ~/.aws/config in case it is not provided here.
    """

    credentials_profile_name: Optional[str] = None
    """The name of the profile in the ~/.aws/credentials or ~/.aws/config files, which
    has either access keys or role information specified.
    If not specified, the default credential profile or, if on an EC2 instance,
    credentials from IMDS will be used.
    See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    """

    model_id: str
    """Id of the model to call, e.g., amazon.titan-tg1-large, this is
    equivalent to the modelId property in the list-foundation-models api"""

    model_endpoint: str
    """SageMaker Endpoint of the model to call, e.g. instruct-endpoint"""

    model_provider: Optional[str] = "CSDC"
    """This model is provided by CSDC"""

    model_kwargs: Optional[Dict] = None
    """Key word arguments to pass to the model."""

    endpoint_url: Optional[str] = None
    """Needed if you don't want to default to us-east-1 endpoint"""

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that AWS credentials to and python package exists in environment."""

        # Skip creating new client if passed in constructor
        if values["client"] is not None:
            return values

        try:
            import boto3

            if values["credentials_profile_name"] is not None:
                session = boto3.Session(profile_name=values["credentials_profile_name"])
            else:
                # use default credentials
                session = boto3.Session()

            client_params = {}
            if values["region_name"]:
                client_params["region_name"] = values["region_name"]
            if values["endpoint_url"]:
                client_params["endpoint_url"] = values["endpoint_url"]

            values["client"] = session.client("sagemaker-runtime", **client_params)

        except ImportError:
            raise ModuleNotFoundError(
                "Could not import boto3 python package. "
                "Please install it with `pip install boto3`."
            )
        except Exception as e:
            raise ValueError(
                "Could not load credentials to authenticate with AWS client. "
                "Please check that credentials in the specified "
                "profile name are valid."
            ) from e

        return values

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        _model_kwargs = self.model_kwargs or {}
        return {
            **{"model_kwargs": _model_kwargs},
        }

    def _get_provider(self) -> str:
        return self.model_provider if self.model_provider else self.model_id.split(".")[0]

    def _prepare_input_and_invoke(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        _model_kwargs = self.model_kwargs or {}

        provider = self._get_provider()
        params = {**_model_kwargs, **kwargs}
        input_body = LLMInputOutputAdapter.prepare_input(provider, prompt, params)
        body = json.dumps(input_body).encode('utf-8')
        accept = "application/json"
        contentType = "application/json"
        endpoint_name = self.model_endpoint

        try:
            response = self.client.invoke_endpoint(
                EndpointName = endpoint_name, Body=body, ContentType=contentType
            )
            text = LLMInputOutputAdapter.prepare_output(provider, response)

        except Exception as e:
            raise ValueError(f"Error raised by invoking CSDC LLM: {e}")

        if stop is not None:
            text = enforce_stop_tokens(text, stop)

        return text


class CSDCLLM(LLM, CSDCLLMBase):
    """CSDC LLM base model.

    To authenticate, the AWS client uses the following methods to
    automatically load credentials:
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html

    If a specific credential profile should be used, you must pass
    the name of the profile from the ~/.aws/credentials file that is to be used.

    Make sure the credentials / roles used have the required policies to
    access the SageMaker service.
    """

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "aws_csdc_llm"

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call out to CSDC LLM model in SageMaker Endpoint.

        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.

        Returns:
            The string generated by the model.

        Example:
            .. code-block:: python

                response = se("Tell me a joke.")
        """

        text = self._prepare_input_and_invoke(prompt=prompt, stop=stop, **kwargs)

        return text