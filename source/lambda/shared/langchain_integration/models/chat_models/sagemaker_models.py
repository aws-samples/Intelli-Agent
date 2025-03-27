import asyncio
import codecs
import io
import json
import os
import threading
import time
import uuid
from functools import reduce
from operator import itemgetter
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)
from urllib.parse import urlparse

import boto3
import botocore
from botocore.exceptions import ClientError, WaiterError
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    BaseMessageChunk,
    ChatMessage,
    ChatMessageChunk,
    FunctionMessage,
    FunctionMessageChunk,
    HumanMessage,
    HumanMessageChunk,
    SystemMessage,
    SystemMessageChunk,
    ToolMessage,
    ToolMessageChunk,
    convert_to_messages,
)
from langchain_core.messages.ai import (
    InputTokenDetails,
    OutputTokenDetails,
    UsageMetadata,
)
from langchain_core.output_parsers.openai_tools import (
    make_invalid_tool_call,
    parse_tool_call,
)
from langchain_core.outputs import (
    ChatGeneration,
    ChatGenerationChunk,
    ChatResult,
)
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
    RunnableMap,
    RunnablePassthrough,
)
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel
from pydantic import BaseModel as pydantic_basemodel
from pydantic import model_validator
from shared.constant import LLMModelType, ModelProvider
from shared.utils.logger_utils import get_logger
from shared.utils.boto3_utils import get_boto3_client
from . import ChatModelBase

# from sagemaker.async_inference

logger = get_logger(__name__)
session = boto3.Session()
current_region = session.region_name

import os
from typing import Optional

from pydantic import BaseModel


class ClientBase(BaseModel):
    model_id: Optional[str] = None
    """The model id deployed by emd."""

    model_tag: Optional[str] = ""
    """The model tag."""

    model_stack_name: Optional[str] = None
    """The name of the model stack deployed by emd."""

    class Config:
        """Configuration for this pydantic object."""

        extra = "allow"

    def invoke(self, pyload: dict):
        raise NotImplementedError

    def invoke_async(self, pyload: dict):
        raise NotADirectoryError


class AsyncInferenceError(Exception):
    """The base exception class for Async Inference exceptions."""

    fmt = "An unspecified error occurred"

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs


class PollingTimeoutError(AsyncInferenceError):
    """Raised when wait longer than expected and no result object in Amazon S3 bucket yet"""

    fmt = "No result at {output_path} after polling for {seconds} seconds. {message}"

    def __init__(self, message, output_path, seconds):
        super().__init__(
            message=message, output_path=output_path, seconds=seconds
        )


class AsyncInferenceModelError(AsyncInferenceError):
    """Raised when model returns errors for failed requests"""

    fmt = "Model returned error: {message} "

    def __init__(self, message):
        super().__init__(message=message)


class UnexpectedClientError(AsyncInferenceError):
    """Raised when ClientError's error code is not expected"""

    fmt = "Encountered unexpected client error: {message}"

    def __init__(self, message):
        super().__init__(message=message)


class ObjectNotExistedError(AsyncInferenceError):
    """Raised when Amazon S3 object not exist in the given path"""

    fmt = "Object not exist at {output_path}. {message}"

    def __init__(self, message, output_path):
        super().__init__(message=message, output_path=output_path)


class LineIterator:
    """
    A helper class for parsing the byte stream input.

    The output of the model will be in the following format:

    b'{"outputs": [" a"]}\n'
    b'{"outputs": [" challenging"]}\n'
    b'{"outputs": [" problem"]}\n'
    ...

    While usually each PayloadPart event from the event stream will
    contain a byte array with a full json, this is not guaranteed
    and some of the json objects may be split acrossPayloadPart events.

    For example:

    {'PayloadPart': {'Bytes': b'{"outputs": '}}
    {'PayloadPart': {'Bytes': b'[" problem"]}\n'}}


    This class accounts for this by concatenating bytes written via the 'write' function
    and then exposing a method which will return lines (ending with a '\n' character)
    within the buffer via the 'scan_lines' function.
    It maintains the position of the last read position to ensure
    that previous bytes are not exposed again.

    For more details see:
    https://aws.amazon.com/blogs/machine-learning/elevating-the-generative-ai-experience-introducing-streaming-support-in-amazon-sagemaker-hosting/
    """

    def __init__(self, stream: Any) -> None:
        self.byte_iterator = iter(stream)
        self.buffer = io.BytesIO()
        self.read_pos = 0

    def __iter__(self) -> "LineIterator":
        return self

    def __next__(self) -> Any:
        while True:
            self.buffer.seek(self.read_pos)
            line = self.buffer.readline()
            if line and line[-1] == ord("\n"):
                self.read_pos += len(line)
                return line[:-1]
            try:
                chunk = next(self.byte_iterator)
            except StopIteration:
                if self.read_pos < self.buffer.getbuffer().nbytes:
                    continue
                raise
            if "PayloadPart" not in chunk:
                # Unknown Event Type
                continue
            self.buffer.seek(0, io.SEEK_END)
            self.buffer.write(chunk["PayloadPart"]["Bytes"])


class WaiterConfig(object):
    """Configuration object passed in when using async inference and wait for the result."""

    def __init__(
        self,
        max_attempts=60,
        delay=15,
    ):
        """Initialize a WaiterConfig object that provides parameters to control waiting behavior.

        Args:
            max_attempts (int): The maximum number of attempts to be made. If the max attempts is
            exceeded, Amazon SageMaker will raise ``PollingTimeoutError``. (Default: 60)
            delay (int): The amount of time in seconds to wait between attempts. (Default: 15)
        """

        self.max_attempts = max_attempts
        self.delay = delay

    def _to_request_dict(self):
        """Generates a dictionary using the parameters provided to the class."""
        waiter_dict = {
            "Delay": self.delay,
            "MaxAttempts": self.max_attempts,
        }

        return waiter_dict


class AsyncInferenceResponse(object):
    """Response from Async Inference endpoint

    This response object provides a method to check for an async inference result in the
    Amazon S3 output path specified. If result object exists in that path, get and return
    the result
    """

    def __init__(
        self,
        predictor_async,
        output_path,
        failure_path,
    ):
        """Initialize an AsyncInferenceResponse object.

        AsyncInferenceResponse can help users to get async inference result
        from the Amazon S3 output path

        Args:
            predictor_async (sagemaker.predictor.AsyncPredictor): The ``AsyncPredictor``
                that return this response.
            output_path (str): The Amazon S3 location that endpoints upload inference responses
                to.
            failure_path (str): The Amazon S3 location that endpoints upload model errors
                for failed requests.
        """
        self.predictor_async = predictor_async
        self.output_path = output_path
        self._result = None
        self.failure_path = failure_path

    def get_result(
        self,
        waiter_config=None,
    ):
        """Get async inference result in the Amazon S3 output path specified

        Args:
            waiter_config (sagemaker.async_inference.waiter_config.WaiterConfig): Configuration
                for the waiter. The pre-defined value for the delay between poll is 15 seconds
                and the default max attempts is 60
        Raises:
            ValueError: If a wrong type of object is provided as ``waiter_config``
        Returns:
            object: Inference result in the given Amazon S3 output path. If a deserializer was
                specified when creating the AsyncPredictor, the result of the deserializer is
                returned. Otherwise the response returns the sequence of bytes
                as is.
        """
        if waiter_config is not None and not isinstance(
            waiter_config, WaiterConfig
        ):
            raise ValueError("waiter_config should be a WaiterConfig object")

        if self._result is None:
            if waiter_config is None:
                self._result = self._get_result_from_s3(
                    self.output_path, self.failure_path
                )
            else:
                self._result = self.predictor_async._wait_for_output(
                    self.output_path, self.failure_path, waiter_config
                )
        return self._result

    def _get_result_from_s3(self, output_path, failure_path):
        """Retrieve output based on the presense of failure_path"""
        if failure_path is not None:
            return self._get_result_from_s3_output_failure_paths(
                output_path, failure_path
            )

        return self._get_result_from_s3_output_path(output_path)

    def _get_result_from_s3_output_path(self, output_path):
        """Get inference result from the output Amazon S3 path"""
        bucket, key = parse_s3_url(output_path)
        try:
            response = self.predictor_async.s3_client.get_object(
                Bucket=bucket, Key=key
            )
            return self.predictor_async.predictor._handle_response(response)
        except ClientError as ex:
            if ex.response["Error"]["Code"] == "NoSuchKey":
                raise ObjectNotExistedError(
                    message="Inference could still be running",
                    output_path=output_path,
                )
            raise UnexpectedClientError(
                message=ex.response["Error"]["Message"],
            )

    def _get_result_from_s3_output_failure_paths(
        self, output_path, failure_path
    ):
        """Get inference result from the output & failure Amazon S3 path"""
        bucket, key = parse_s3_url(output_path)
        try:
            response = self.predictor_async.s3_client.get_object(
                Bucket=bucket, Key=key
            )
            return self.predictor_async._handle_response(response)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                try:
                    failure_bucket, failure_key = parse_s3_url(failure_path)
                    failure_response = (
                        self.predictor_async.s3_client.get_object(
                            Bucket=failure_bucket, Key=failure_key
                        )
                    )
                    failure_response = self.predictor_async._handle_response(
                        failure_response
                    )
                    raise AsyncInferenceModelError(message=failure_response)
                except ClientError as ex:
                    if ex.response["Error"]["Code"] == "NoSuchKey":
                        raise ObjectNotExistedError(
                            message="Inference could still be running",
                            output_path=output_path,
                        )
                    raise UnexpectedClientError(
                        message=ex.response["Error"]["Message"]
                    )
            raise UnexpectedClientError(message=e.response["Error"]["Message"])


def parse_s3_url(url):
    """Returns an (s3 bucket, key name/prefix) tuple from a url with an s3 scheme.

    Args:
        url (str):

    Returns:
        tuple: A tuple containing:

            - str: S3 bucket name
            - str: S3 key
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme != "s3":
        raise ValueError(
            "Expecting 's3' scheme, got: {} in {}.".format(
                parsed_url.scheme, url
            )
        )
    return parsed_url.netloc, parsed_url.path.lstrip("/")


def sagemaker_timestamp():
    """Return a timestamp with millisecond precision."""
    moment = time.time()
    moment_ms = repr(moment).split(".")[1][:3]
    return time.strftime(
        "%Y-%m-%d-%H-%M-%S-{}".format(moment_ms), time.gmtime(moment)
    )


def sagemaker_short_timestamp():
    """Return a timestamp that is relatively short in length"""
    return time.strftime("%y%m%d-%H%M")


def s3_path_join(*args, with_end_slash: bool = False):
    """Returns the arguments joined by a slash ("/"), similar to ``os.path.join()`` (on Unix).

    Behavior of this function:
    - If the first argument is "s3://", then that is preserved.
    - The output by default will have no slashes at the beginning or end. There is one exception
        (see `with_end_slash`). For example, `s3_path_join("/foo", "bar/")` will yield
        `"foo/bar"` and `s3_path_join("foo", "bar", with_end_slash=True)` will yield `"foo/bar/"`
    - Any repeat slashes will be removed in the output (except for "s3://" if provided at the
        beginning). For example, `s3_path_join("s3://", "//foo/", "/bar///baz")` will yield
        `"s3://foo/bar/baz"`.
    - Empty or None arguments will be skipped. For example
        `s3_path_join("foo", "", None, "bar")` will yield `"foo/bar"`

    Alternatives to this function that are NOT recommended for S3 paths:
    - `os.path.join(...)` will have different behavior on Unix machines vs non-Unix machines
    - `pathlib.PurePosixPath(...)` will apply potentially unintended simplification of single
        dots (".") and root directories. (for example
        `pathlib.PurePosixPath("foo", "/bar/./", "baz")` would yield `"/bar/baz"`)
    - `"{}/{}/{}".format(...)` and similar may result in unintended repeat slashes

    Args:
        *args: The strings to join with a slash.
        with_end_slash (bool): (default: False) If true and if the path is not empty, appends a "/"
            to the end of the path

    Returns:
        str: The joined string, without a slash at the end unless with_end_slash is True.
    """
    delimiter = "/"

    non_empty_args = list(
        filter(lambda item: item is not None and item != "", args)
    )

    merged_path = ""
    for index, path in enumerate(non_empty_args):
        if (
            index == 0
            or (merged_path and merged_path[-1] == delimiter)
            or (path and path[0] == delimiter)
        ):
            # dont need to add an extra slash because either this is the beginning of the string,
            # or one (or more) slash already exists
            merged_path += path
        else:
            merged_path += delimiter + path

    if with_end_slash and merged_path and merged_path[-1] != delimiter:
        merged_path += delimiter

    # At this point, merged_path may include slashes at the beginning and/or end. And some of the
    # provided args may have had duplicate slashes inside or at the ends.
    # For backwards compatibility reasons, these need to be filtered out (done below). In the
    # future, if there is a desire to support multiple slashes for S3 paths throughout the SDK,
    # one option is to create a new optional argument (or a new function) that only executes the
    # logic above.
    filtered_path = merged_path
    # remove duplicate slashes
    if filtered_path:

        def duplicate_delimiter_remover(sequence, next_char):
            if sequence[-1] == delimiter and next_char == delimiter:
                return sequence
            return sequence + next_char

        if filtered_path.startswith("s3://"):
            filtered_path = reduce(
                duplicate_delimiter_remover,
                filtered_path[5:],
                filtered_path[:5],
            )
        else:
            filtered_path = reduce(duplicate_delimiter_remover, filtered_path)

    # remove beginning slashes
    filtered_path = filtered_path.lstrip(delimiter)

    # remove end slashes
    if not with_end_slash and filtered_path != "s3://":
        filtered_path = filtered_path.rstrip(delimiter)

    return filtered_path


def name_from_base(base, max_length=63, short=False):
    """Append a timestamp to the provided string.

    This function assures that the total length of the resulting string is
    not longer than the specified max length, trimming the input parameter if
    necessary.

    Args:
        base (str): String used as prefix to generate the unique name.
        max_length (int): Maximum length for the resulting string (default: 63).
        short (bool): Whether or not to use a truncated timestamp (default: False).

    Returns:
        str: Input parameter with appended timestamp.
    """
    timestamp = sagemaker_short_timestamp() if short else sagemaker_timestamp()
    trimmed_base = base[: max_length - len(timestamp) - 1]
    return "{}-{}".format(trimmed_base, timestamp)


def _botocore_resolver():
    """Get the DNS suffix for the given region.

    Args:
        region (str): AWS region name

    Returns:
        str: the DNS suffix
    """
    loader = botocore.loaders.create_loader()
    return botocore.regions.EndpointResolver(loader.load_data("endpoints"))


def sts_regional_endpoint(region):
    """Get the AWS STS endpoint specific for the given region.

    We need this function because the AWS SDK does not yet honor
    the ``region_name`` parameter when creating an AWS STS client.

    For the list of regional endpoints, see
    https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_enable-regions.html#id_credentials_region-endpoints.

    Args:
        region (str): AWS region name

    Returns:
        str: AWS STS regional endpoint
    """
    endpoint_data = _botocore_resolver().construct_endpoint("sts", region)
    if region == "il-central-1" and not endpoint_data:
        endpoint_data = {"hostname": "sts.{}.amazonaws.com".format(region)}
    return "https://{}".format(endpoint_data["hostname"])


def generate_default_sagemaker_bucket_name(boto_session):
    """Generates a name for the default sagemaker S3 bucket.

    Args:
        boto_session (boto3.session.Session): The underlying Boto3 session which AWS service
    """
    region = boto_session.region_name
    account = boto_session.client(
        "sts", region_name=region, endpoint_url=sts_regional_endpoint(region)
    ).get_caller_identity()["Account"]
    return "sagemaker-{}-{}".format(region, account)


class SageMakerClient(ClientBase):
    boto_session: Any = None

    name: str = None
    """The name of the Sagemaker client, used for logging purposes."""

    client: Any = None
    """Boto3 client for sagemaker runtime"""

    endpoint_name: Union[str, None] = None
    """The name of the endpoint from the deployed Sagemaker model.
    Must be unique within an AWS Region."""

    region_name: Union[str, None] = None
    """The aws region where the Sagemaker model is deployed, eg. `us-west-2`."""

    credentials_profile_name: Union[str, None] = None
    """The name of the profile in the ~/.aws/credentials or ~/.aws/config files, which
    has either access keys or role information specified.
    If not specified, the default credential profile or, if on an EC2 instance,
    credentials from IMDS will be used.
    See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    """

    model_kwargs: Optional[Dict] = None
    """Keyword arguments to pass to the model."""

    endpoint_kwargs: Optional[Dict] = None
    """Optional attributes passed to the invoke_endpoint
    function. See `boto3`_. docs for more info.
    .. _boto3: <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>
    """

    default_bucket: Union[str, None] = None
    """Default bucket to use for async inference if not specified in the request"""

    default_bucket_prefix: Union[str, None] = None
    """Default bucket prefix to use for async inference if not specified in the request"""

    s3_client: Any = None
    """Boto3 client for s3"""

    @model_validator(mode="before")
    def validate_environment(cls, values: Dict) -> Dict:
        """Dont do anything if client provided externally"""
        if not values.get("client"):
            """Validate that AWS credentials to and python package exists in environment."""
            try:
                import boto3

                try:
                    if not values.get("boto_session"):
                        if values.get("credentials_profile_name") is not None:
                            boto_session = boto3.Session(
                                profile_name=values["credentials_profile_name"]
                            )
                        else:
                            # use default credentials
                            boto_session = boto3.Session()
                        values["boto_session"] = boto_session

                    values["client"] = values["boto_session"].client(
                        "sagemaker-runtime",
                        region_name=values.get("region_name"),
                    )
                    if values.get("s3_client") is None:
                        values["s3_client"] = values["boto_session"].client(
                            "s3", region_name=values.get("region_name")
                        )

                except Exception as e:
                    import traceback

                    logger.error(traceback.format_exc())
                    raise ValueError(
                        "Could not load credentials to authenticate with AWS client. "
                        "Please check that credentials in the specified "
                        "profile name are valid."
                    ) from e

            except ImportError:
                raise ImportError(
                    "Could not import boto3 python package. "
                    "Please install it with `pip install boto3`."
                )

        if values.get("endpoint_name"):
            return values

        # model_stack_name = values.get("model_stack_name")
        # if model_stack_name is None:
        #     # check if stack is ready
        #     model_id = values.get("model_id")
        #     if model_id is None:
        #         raise ValueError(
        #             "model_id or model_stack_name must be provided"
        #         )
        #     model_stack_name = Model.get_model_stack_name_prefix(
        #         model_id, model_tag=values.get("model_tag") or MODEL_DEFAULT_TAG
        #     )

        # # get endpoint name from stack
        # if not check_stack_exists(model_stack_name):
        #     raise ValueError(f"Model stack {model_stack_name} does not exist")

        # stack_info = get_model_stack_info(model_stack_name)

        # Outputs = stack_info.get("Outputs")
        # if not Outputs:
        #     raise RuntimeError(
        #         f"Model stack {model_stack_name} does not have any outputs, the model may be not deployed in success"
        #     )
        # for output in Outputs:
        #     if output["OutputKey"] == "SageMakerEndpointName":
        #         values["endpoint_name"] = output["OutputValue"]
        #         break

        # assert (
        #     values.get("endpoint_name") is not None
        # ), "Endpoint name not found in stack outputs"

        # if not values.get("name"):
        #     values["name"] = model_stack_name
        # return values

    def _prepare_input_body(self, pyload: dict):
        _model_kwargs = self.model_kwargs or {}
        body = json.dumps(
            {**_model_kwargs, **pyload}, ensure_ascii=False, indent=2
        )
        accept = "application/json"
        contentType = "application/json"
        _endpoint_kwargs = self.endpoint_kwargs or {}
        request_options = {
            "Body": body,
            "EndpointName": self.endpoint_name,
            "Accept": accept,
            "ContentType": contentType,
            **_endpoint_kwargs,
        }
        enable_print_messages = os.getenv(
            "ENABLE_PRINT_MESSAGES", "False"
        ).lower() in ("true", "1", "t")
        if enable_print_messages:
            logger.info(f"request body: {json.loads(request_options['Body'])}")
        return request_options

    def invoke(self, pyload: dict):
        request_options = self._prepare_input_body(pyload)
        stream = pyload.get("stream", False)
        if stream:
            resp = self.client.invoke_endpoint_with_response_stream(
                **request_options
            )

            def _ret_iterator_helper():
                iterator = LineIterator(resp["Body"])
                for line in iterator:
                    chunk_dict = json.loads(line)
                    if not chunk_dict:
                        continue
                    yield chunk_dict

            return _ret_iterator_helper()
        else:
            output = self.client.invoke_endpoint(**request_options)["Body"]
            response_dict = json.loads(output.read().decode("utf-8"))
            return response_dict

    def account_id(self) -> str:
        """Get the AWS account id of the caller.

        Returns:
            AWS account ID.
        """
        region = self.boto_session.region_name
        sts_client = self.boto_session.client(
            "sts",
            region_name=region,
            endpoint_url=sts_regional_endpoint(region),
        )
        return sts_client.get_caller_identity()["Account"]

    def general_bucket_check_if_user_has_permission(
        self, bucket_name, s3, bucket, region, bucket_creation_date_none
    ):
        """Checks if the person running has the permissions to the bucket

        If there is any other error that comes up with calling head bucket, it is raised up here
        If there is no bucket , it will create one

        Args:
            bucket_name (str): Name of the S3 bucket
            s3 (str): S3 object from boto session
            region (str): The region in which to create the bucket.
            bucket_creation_date_none (bool):Indicating whether S3 bucket already exists or not
        """
        try:
            s3.meta.client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            message = e.response["Error"]["Message"]
            # bucket does not exist or forbidden to access
            if bucket_creation_date_none:
                if error_code == "404" and message == "Not Found":
                    self.create_bucket_for_not_exist_error(
                        bucket_name, region, s3
                    )
                elif error_code == "403" and message == "Forbidden":
                    logger.error(
                        "Bucket %s exists, but access is forbidden. Please try again after "
                        "adding appropriate access.",
                        bucket.name,
                    )
                    raise
                else:
                    raise

    def expected_bucket_owner_id_bucket_check(
        self, bucket_name, s3, expected_bucket_owner_id
    ):
        """Checks if the bucket belongs to a particular owner and throws a Client Error if it is not

        Args:
            bucket_name (str): Name of the S3 bucket
            s3 (str): S3 object from boto session
            expected_bucket_owner_id (str): Owner ID string

        """
        try:
            s3.meta.client.head_bucket(
                Bucket=bucket_name, ExpectedBucketOwner=expected_bucket_owner_id
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            message = e.response["Error"]["Message"]
            if error_code == "403" and message == "Forbidden":
                logger.error(
                    "Since default_bucket param was not set, SageMaker Python SDK tried to use "
                    "%s bucket. "
                    "This bucket cannot be configured to use as it is not owned by Account %s. "
                    "To unblock it's recommended to use custom default_bucket "
                    "parameter in sagemaker.Session",
                    bucket_name,
                    expected_bucket_owner_id,
                )
                raise

    def _create_s3_bucket_if_it_does_not_exist(self, bucket_name, region):
        """Creates an S3 Bucket if it does not exist.

        Also swallows a few common exceptions that indicate that the bucket already exists or
        that it is being created.

        Args:
            bucket_name (str): Name of the S3 bucket to be created.
            region (str): The region in which to create the bucket.

        Raises:
            botocore.exceptions.ClientError: If S3 throws an unexpected exception during bucket
                creation.
                If the exception is due to the bucket already existing or
                already being created, no exception is raised.
        """

        s3 = self.boto_session.resource("s3", region_name=region)

        bucket = s3.Bucket(name=bucket_name)
        if bucket.creation_date is None:
            self.general_bucket_check_if_user_has_permission(
                bucket_name, s3, bucket, region, True
            )
        else:
            self.general_bucket_check_if_user_has_permission(
                bucket_name, s3, bucket, region, False
            )

            expected_bucket_owner_id = self.account_id()
            self.expected_bucket_owner_id_bucket_check(
                bucket_name, s3, expected_bucket_owner_id
            )

        # self.general_bucket_check_if_user_has_permission(bucket_name, s3, bucket, region, False)

        # expected_bucket_owner_id = self.account_id()
        # self.expected_bucket_owner_id_bucket_check(bucket_name, s3, expected_bucket_owner_id)

    def create_bucket_for_not_exist_error(self, bucket_name, region, s3):
        """Creates the S3 bucket in the given region

        Args:
            bucket_name (str): Name of the S3 bucket
            s3 (str): S3 object from boto session
            region (str): The region in which to create the bucket.
        """
        # bucket does not exist, create one
        try:
            if region == "us-east-1":
                # 'us-east-1' cannot be specified because it is the default region:
                # https://github.com/boto/boto3/issues/125
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )

            logger.info("Created S3 bucket: %s", bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            message = e.response["Error"]["Message"]

            if (
                error_code == "OperationAborted"
                and "conflicting conditional operation" in message
            ):
                # If this bucket is already being concurrently created,
                # we don't need to create it again.
                pass
            else:
                raise

    def get_default_bucket(self):
        """Return the name of the default bucket to use in relevant Amazon SageMaker interactions.

        This function will create the s3 bucket if it does not exist.

        Returns:
            str: The name of the default bucket. If the name was not explicitly specified through
                the Session or sagemaker_config, the bucket will take the form:
                ``sagemaker-{region}-{AWS account ID}``.
        """

        if self.default_bucket:
            return self.default_bucket

        region = self.boto_session.region_name

        default_bucket = generate_default_sagemaker_bucket_name(
            self.boto_session
        )

        self._create_s3_bucket_if_it_does_not_exist(
            bucket_name=default_bucket,
            region=region,
        )

        self.default_bucket = default_bucket

        return self.default_bucket

    def _upload_data_to_s3(
        self,
        data,
        input_path=None,
    ):
        """Upload request data to Amazon S3 for users"""
        if input_path:
            bucket, key = parse_s3_url(input_path)
        else:
            my_uuid = str(uuid.uuid4())
            timestamp = sagemaker_timestamp()
            bucket = self.get_default_bucket()
            key = s3_path_join(
                self.default_bucket_prefix,
                "async-endpoint-inputs",
                name_from_base(self.name, short=True),
                "{}-{}".format(timestamp, my_uuid),
            )

        _model_kwargs = self.model_kwargs or {}
        data = json.dumps(
            {**_model_kwargs, **data}, ensure_ascii=False, indent=2
        )
        self.s3_client.put_object(
            Body=data, Bucket=bucket, Key=key, ContentType="application/json"
        )
        input_path = input_path or "s3://{}/{}".format(bucket, key)

        return input_path

    def _handle_response(self, response):
        response_body = response["Body"]
        content_type = response.get("ContentType", "application/octet-stream")
        try:
            return json.load(codecs.getreader("utf-8")(response_body))
        finally:
            response_body.close()

    def _check_output_and_failure_paths(
        self, output_path, failure_path, waiter_config
    ):
        """Check the Amazon S3 output path for the output.

        This method waits for either the output file or the failure file to be found on the
        specified S3 output path. Whichever file is found first, its corresponding event is
        triggered, and the method executes the appropriate action based on the event.

        Args:
            output_path (str): The S3 path where the output file is expected to be found.
            failure_path (str): The S3 path where the failure file is expected to be found.
            waiter_config (boto3.waiter.WaiterConfig): The configuration for the S3 waiter.

        Returns:
            Any: The deserialized result from the output file, if the output file is found first.
            Otherwise, raises an exception.

        Raises:
            AsyncInferenceModelError: If the failure file is found before the output file.
            PollingTimeoutError: If both files are not found and the S3 waiter
             has thrown a WaiterError.
        """
        output_bucket, output_key = parse_s3_url(output_path)
        failure_bucket, failure_key = parse_s3_url(failure_path)

        output_file_found = threading.Event()
        failure_file_found = threading.Event()

        def check_output_file():
            try:
                output_file_waiter = self.s3_client.get_waiter("object_exists")
                output_file_waiter.wait(
                    Bucket=output_bucket,
                    Key=output_key,
                    WaiterConfig=waiter_config._to_request_dict(),
                )
                output_file_found.set()
            except WaiterError:
                pass

        def check_failure_file():
            try:
                failure_file_waiter = self.s3_client.get_waiter("object_exists")
                failure_file_waiter.wait(
                    Bucket=failure_bucket,
                    Key=failure_key,
                    WaiterConfig=waiter_config._to_request_dict(),
                )
                failure_file_found.set()
            except WaiterError:
                pass

        output_thread = threading.Thread(target=check_output_file)
        failure_thread = threading.Thread(target=check_failure_file)

        output_thread.start()
        failure_thread.start()

        while (
            not output_file_found.is_set() and not failure_file_found.is_set()
        ):
            time.sleep(1)

        if output_file_found.is_set():
            s3_object = self.s3_client.get_object(
                Bucket=output_bucket, Key=output_key
            )
            result = self._handle_response(response=s3_object)
            return result

        failure_object = self.s3_client.get_object(
            Bucket=failure_bucket, Key=failure_key
        )
        failure_response = self._handle_response(response=failure_object)

        raise (
            AsyncInferenceModelError(message=failure_response)
            if failure_file_found.is_set()
            else PollingTimeoutError(
                message="Inference could still be running",
                output_path=output_path,
                seconds=waiter_config.delay * waiter_config.max_attempts,
            )
        )

    def _check_output_path(self, output_path, waiter_config):
        """Check the Amazon S3 output path for the output.

        Periodically check Amazon S3 output path for async inference result.
        Timeout automatically after max attempts reached
        """
        bucket, key = parse_s3_url(output_path)
        s3_waiter = self.s3_client.get_waiter("object_exists")
        try:
            s3_waiter.wait(
                Bucket=bucket,
                Key=key,
                WaiterConfig=waiter_config._to_request_dict(),
            )
        except WaiterError:
            raise PollingTimeoutError(
                message="Inference could still be running",
                output_path=output_path,
                seconds=waiter_config.delay * waiter_config.max_attempts,
            )
        s3_object = self.s3_client.get_object(Bucket=bucket, Key=key)
        result = self._handle_response(response=s3_object)
        return result

    def _wait_for_output(self, output_path, failure_path, waiter_config):
        """Retrieve output based on the presense of failure_path."""
        if failure_path is not None:
            return self._check_output_and_failure_paths(
                output_path, failure_path, waiter_config
            )

        return self._check_output_path(output_path, waiter_config)

    def invoke_async(
        self,
        data: dict = None,
        input_path=None,
        inference_id=None,
        waiter_config=WaiterConfig(delay=0.1, max_attempts=15 * 60 / 0.1),
        async_invoke=False,
    ):
        if data is None and input_path is None:
            raise ValueError(
                "Please provide data or input_path Amazon S3 location to use async prediction"
            )
        if data is not None:
            input_path = self._upload_data_to_s3(data, input_path)

        request_options = {
            "InputLocation": input_path,
            "EndpointName": self.endpoint_name,
            "Accept": "*/*",
        }
        if inference_id:
            request_options["InferenceId"]

        response = self.client.invoke_endpoint_async(**request_options)
        output_location = response["OutputLocation"]
        failure_location = response.get("FailureLocation")
        if async_invoke:
            response_async = AsyncInferenceResponse(
                predictor_async=self,
                output_path=output_location,
                failure_path=failure_location,
            )
            return response_async
        else:
            result = self._wait_for_output(
                output_path=output_location,
                failure_path=failure_location,
                waiter_config=waiter_config,
            )
        return result


def _convert_dict_to_message(_dict: Mapping[str, Any]) -> BaseMessage:
    """Convert a dictionary to a LangChain message.

    Args:
        _dict: The dictionary.

    Returns:
        The LangChain message.
    """
    role = _dict.get("role")
    name = _dict.get("name")
    id_ = _dict.get("id")
    if role == "user":
        return HumanMessage(content=_dict.get("content", ""), id=id_, name=name)
    elif role == "assistant":
        # Fix for azure
        # Also OpenAI returns None for tool invocations
        content = _dict.get("content", "") or ""
        additional_kwargs: Dict = {}
        if function_call := _dict.get("function_call"):
            additional_kwargs["function_call"] = dict(function_call)
        tool_calls = []
        invalid_tool_calls = []
        if raw_tool_calls := _dict.get("tool_calls"):
            additional_kwargs["tool_calls"] = raw_tool_calls
            for raw_tool_call in raw_tool_calls:
                try:
                    tool_calls.append(
                        parse_tool_call(raw_tool_call, return_id=True)
                    )
                except Exception as e:
                    invalid_tool_calls.append(
                        make_invalid_tool_call(raw_tool_call, str(e))
                    )
        if audio := _dict.get("audio"):
            additional_kwargs["audio"] = audio
        return AIMessage(
            content=content,
            additional_kwargs=additional_kwargs,
            name=name,
            id=id_,
            tool_calls=tool_calls,
            invalid_tool_calls=invalid_tool_calls,
        )
    elif role == "system":
        return SystemMessage(
            content=_dict.get("content", ""), name=name, id=id_
        )
    elif role == "function":
        return FunctionMessage(
            content=_dict.get("content", ""),
            name=cast(str, _dict.get("name")),
            id=id_,
        )
    elif role == "tool":
        additional_kwargs = {}
        if "name" in _dict:
            additional_kwargs["name"] = _dict["name"]
        return ToolMessage(
            content=_dict.get("content", ""),
            tool_call_id=cast(str, _dict.get("tool_call_id")),
            additional_kwargs=additional_kwargs,
            name=name,
            id=id_,
        )
    else:
        return ChatMessage(content=_dict.get("content", ""), role=role, id=id_)  # type: ignore[arg-type]


def _create_usage_metadata(oai_token_usage: dict) -> UsageMetadata:
    input_tokens = oai_token_usage.get("prompt_tokens", 0)
    output_tokens = oai_token_usage.get("completion_tokens", 0)
    total_tokens = oai_token_usage.get(
        "total_tokens", input_tokens + output_tokens
    )
    input_token_details: dict = {
        "audio": (oai_token_usage.get("prompt_tokens_details") or {}).get(
            "audio_tokens"
        ),
        "cache_read": (oai_token_usage.get("prompt_tokens_details") or {}).get(
            "cached_tokens"
        ),
    }
    output_token_details: dict = {
        "audio": (oai_token_usage.get("completion_tokens_details") or {}).get(
            "audio_tokens"
        ),
        "reasoning": (
            oai_token_usage.get("completion_tokens_details") or {}
        ).get("reasoning_tokens"),
    }
    return UsageMetadata(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_token_details=InputTokenDetails(
            **{k: v for k, v in input_token_details.items() if v is not None}
        ),
        output_token_details=OutputTokenDetails(
            **{k: v for k, v in output_token_details.items() if v is not None}
        ),
    )


def _convert_delta_to_message_chunk(
    _dict: Mapping[str, Any], default_class: Type[BaseMessageChunk]
) -> BaseMessageChunk:
    role = _dict.get("role")
    content = _dict.get("content") or ""
    additional_kwargs: Dict = {}
    if _dict.get("function_call"):
        function_call = dict(_dict["function_call"])
        if "name" in function_call and function_call["name"] is None:
            function_call["name"] = ""
        additional_kwargs["function_call"] = function_call
    if _dict.get("tool_calls"):
        additional_kwargs["tool_calls"] = _dict["tool_calls"]

    if role == "user" or default_class == HumanMessageChunk:
        return HumanMessageChunk(content=content)
    elif role == "assistant" or default_class == AIMessageChunk:
        return AIMessageChunk(
            content=content, additional_kwargs=additional_kwargs
        )
    elif role == "system" or default_class == SystemMessageChunk:
        return SystemMessageChunk(content=content)
    elif role == "function" or default_class == FunctionMessageChunk:
        return FunctionMessageChunk(content=content, name=_dict["name"])
    elif role == "tool" or default_class == ToolMessageChunk:
        return ToolMessageChunk(
            content=content, tool_call_id=_dict["tool_call_id"]
        )
    elif role or default_class == ChatMessageChunk:
        return ChatMessageChunk(content=content, role=role)  # type: ignore[arg-type]
    else:
        return default_class(content=content)  # type: ignore[call-arg]


class SageMakerVllmModelBase(BaseModel):
    sagemaker_client: Union[SageMakerClient, None] = None

    model_id: Union[str, None] = None
    """The model id deployed by emd."""

    model_tag: Union[str, None] = None
    """The model tag."""

    model_stack_name: Optional[str] = None
    """The name of the model stack deployed by emd."""

    endpoint_name: str = ""
    """The name of the endpoint from the deployed Sagemaker model.
    Must be unique within an AWS Region."""

    region_name: Union[str, None] = None
    """The aws region where the Sagemaker model is deployed, eg. `us-west-2`."""

    credentials_profile_name: Union[str, None] = None
    """The name of the profile in the ~/.aws/credentials or ~/.aws/config files, which
    has either access keys or role information specified.
    If not specified, the default credential profile or, if on an EC2 instance,
    credentials from IMDS will be used.
    See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    """

    model_kwargs: Optional[Dict] = None
    """Keyword arguments to pass to the model."""

    endpoint_kwargs: Optional[Dict] = None
    """Optional attributes passed to the invoke_endpoint
    function. See `boto3`_. docs for more info.
    .. _boto3: <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>
    """

    default_bucket: str = None
    """Default bucket to use for async inference if not specified in the request"""

    default_bucket_prefix: str = None
    """Default bucket prefix to use for async inference if not specified in the request"""

    s3_client: Any = None
    """Boto3 client for s3"""

    class Config:
        """Configuration for this pydantic object."""

        extra = "allow"

    @model_validator(mode="before")
    def validate_environment(cls, values: Dict) -> Dict:
        """Dont do anything if client provided externally"""
        if not values.get("sagemaker_client"):
            region_name=values.get("region_name")
            credentials_profile_name=values.get("credentials_profile_name")
            client = get_boto3_client(
                "sagemaker-runtime",
                profile_name=credentials_profile_name,
                region_name=region_name,
            )
            values["sagemaker_client"] = SageMakerClient(
                client=client,
                region_name=values.get("region_name"),
                endpoint_name=values.get("endpoint_name"),
                endpoint_kwargs=values.get("endpoint_kwargs"),
                default_bucket=values.get("default_bucket"),
                default_bucket_prefix=values.get("default_bucket_prefix"),
                s3_client=values.get("s3_client"),
                credentials_profile_name=values.get("credentials_profile_name"),
                model_kwargs=values.get("model_kwargs", {}),
                model_id=values.get("model_id"),
                model_tag=values.get("model_tag"),
                model_stack_name=values.get("model_stack_name"),
            )
        return values

    async def run_tasks_in_executor(self, tasks: list[dict]):
        loop = asyncio.get_event_loop()
        results = []
        for task in tasks:
            result = loop.run_in_executor(
                None, task["func"], *task.get("args", tuple())
            )
            results.append(result)
        return await asyncio.gather(*results)


class SageMakerVllmChatModelBase(SageMakerVllmModelBase, BaseChatModel):

    def prepare_input_body(
        self, model_kwargs, messages: List[BaseMessage]
    ) -> Dict:
        raise NotImplementedError

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Override the _generate method to implement the chat model logic.

        This can be a call to an API, a call to a local model, or any other
        implementation that generates a response to the input prompt.

        Args:
            messages: the prompt composed of a list of messages.
            stop: a list of strings on which the model should stop generating.
                  If generation stops due to a stop token, the stop token itself
                  SHOULD BE INCLUDED as part of the output. This is not enforced
                  across models right now, but it's a good practice to follow since
                  it makes it much easier to parse the output of the model
                  downstream and understand why generation stopped.
            run_manager: A run manager with callbacks for the LLM.
        """
        # Replace this with actual logic to generate a response from a list
        # of messages.
        _model_kwargs = self.model_kwargs or {}
        _model_kwargs = {**_model_kwargs, **kwargs}

        input_body = self.prepare_input_body(_model_kwargs, messages)
        input_body["stream"] = False
        response_dict = self.sagemaker_client.invoke(input_body)
        generations = []
        generation_info = None
        token_usage = response_dict.get("usage")
        for res in response_dict["choices"]:
            message = _convert_dict_to_message(res["message"])
            if token_usage and isinstance(message, AIMessage):
                message.usage_metadata = _create_usage_metadata(token_usage)
            generation_info = generation_info or {}
            generation_info["finish_reason"] = (
                res.get("finish_reason")
                if res.get("finish_reason") is not None
                else generation_info.get("finish_reason")
            )
            if "logprobs" in res:
                generation_info["logprobs"] = res["logprobs"]
            gen = ChatGeneration(
                message=message, generation_info=generation_info
            )
            generations.append(gen)
        llm_output = {
            "token_usage": token_usage,
            "model_name": response_dict.get("model", self.endpoint_name),
            "system_fingerprint": response_dict.get("system_fingerprint", ""),
        }
        return ChatResult(generations=generations, llm_output=llm_output)

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream the output of the model."""
        _model_kwargs = self.model_kwargs or {}
        _model_kwargs = {**_model_kwargs, **kwargs}
        input_body = self.prepare_input_body(_model_kwargs, messages)
        input_body["stream"] = True
        iterator = self.sagemaker_client.invoke(input_body)

        for chunk_dict in iterator:
            if not chunk_dict:
                continue
            if len(chunk_dict["choices"]) == 0:
                continue
            choice = chunk_dict["choices"][0]
            if choice["delta"] is None:
                continue

            default_chunk_class = AIMessageChunk
            chunk = _convert_delta_to_message_chunk(
                choice["delta"], default_chunk_class
            )
            finish_reason = choice.get("finish_reason")
            generation_info = (
                dict(finish_reason=finish_reason)
                if finish_reason is not None
                else None
            )
            default_chunk_class = chunk.__class__
            cg_chunk = ChatGenerationChunk(
                message=chunk, generation_info=generation_info
            )
            if run_manager:
                run_manager.on_llm_new_token(cg_chunk.text, chunk=cg_chunk)
            yield cg_chunk

    @property
    def _llm_type(self) -> str:
        """Get the type of language model used by this chat model."""
        return "sagemaker-vllm-chat-model"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return a dictionary of identifying parameters.

        This information is used by the LangChain callback system, which
        is used for tracing purposes make it possible to monitor LLMs.
        """
        return {
            # The model name allows users to specify custom token counting
            # rules in LLM monitoring applications (e.g., in LangSmith users
            # can provide per token pricing for their model and monitor
            # costs for the given LLM.)
            "endpoint_name": self.endpoint_name,
        }

    def parse_result(self, message: AIMessage, schema: Type[BaseModel]):
        try:
            data = json.loads(message.content)
        except json.decoder.JSONDecodeError:
            print("json error: ", message)
            raise
        return schema(**data)

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], Type, Callable, BaseTool]],
        *,
        tool_choice: Optional[
            Union[dict, str, Literal["auto", "none", "required", "any"], bool]
        ] = None,
        strict: Optional[bool] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tool-like objects to this chat model.

        Assumes model is compatible with OpenAI tool-calling API.

        Args:
            tools: A list of tool definitions to bind to this chat model.
                Supports any tool definition handled by
                :meth:`langchain_core.utils.function_calling.convert_to_openai_tool`.
            tool_choice: Which tool to require the model to call. Options are:

                - str of the form ``"<<tool_name>>"``: calls <<tool_name>> tool.
                - ``"auto"``: automatically selects a tool (including no tool).
                - ``"none"``: does not call a tool.
                - ``"any"`` or ``"required"`` or ``True``: force at least one tool to be called.
                - dict of the form ``{"type": "function", "function": {"name": <<tool_name>>}}``: calls <<tool_name>> tool.
                - ``False`` or ``None``: no effect, default OpenAI behavior.
            strict: If True, model output is guaranteed to exactly match the JSON Schema
                provided in the tool definition. If True, the input schema will be
                validated according to
                https://platform.openai.com/docs/guides/structured-outputs/supported-schemas.
                If False, input schema will not be validated and model output will not
                be validated.
                If None, ``strict`` argument will not be passed to the model.
            kwargs: Any additional parameters are passed directly to
                :meth:`~langchain_openai.chat_models.base.ChatOpenAI.bind`.

        .. versionchanged:: 0.1.21

            Support for ``strict`` argument added.

        """  # noqa: E501

        formatted_tools = [
            convert_to_openai_tool(tool, strict=strict) for tool in tools
        ]
        if tool_choice:
            if isinstance(tool_choice, str):
                # tool_choice is a tool/function name
                if tool_choice not in ("auto", "none", "any", "required"):
                    tool_choice = {
                        "type": "function",
                        "function": {"name": tool_choice},
                    }
                # 'any' is not natively supported by OpenAI API.
                # We support 'any' since other models use this instead of 'required'.
                if tool_choice == "any":
                    tool_choice = "required"
            elif isinstance(tool_choice, bool):
                tool_choice = "required"
            elif isinstance(tool_choice, dict):
                tool_names = [
                    formatted_tool["function"]["name"]
                    for formatted_tool in formatted_tools
                ]
                if not any(
                    tool_name == tool_choice["function"]["name"]
                    for tool_name in tool_names
                ):
                    raise ValueError(
                        f"Tool choice {tool_choice} was specified, but the only "
                        f"provided tools were {tool_names}."
                    )
            else:
                raise ValueError(
                    f"Unrecognized tool_choice type. Expected str, bool or dict. "
                    f"Received: {tool_choice}"
                )
            kwargs["tool_choice"] = tool_choice
        return super().bind(tools=formatted_tools, **kwargs)

    def with_structured_output(
        self,
        schema: Union[pydantic_basemodel, BaseModel],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, Union[Dict, BaseModel]]:
        assert issubclass(schema, (pydantic_basemodel, BaseModel)), schema
        llm = self.bind(guided_json=schema.schema())
        output_parser = RunnableLambda(lambda x: self.parse_result(x, schema))
        if include_raw:
            parser_assign = RunnablePassthrough.assign(
                parsed=itemgetter("raw") | output_parser,
                parsing_error=lambda _: None,
            )
            parser_none = RunnablePassthrough.assign(parsed=lambda _: None)
            parser_with_fallback = parser_assign.with_fallbacks(
                [parser_none], exception_key="parsing_error"
            )
            return RunnableMap(raw=llm) | parser_with_fallback
        else:
            return llm | output_parser


class _SageMakerVllmChatModel(SageMakerVllmChatModelBase):
    def prepare_input_body(
        self, model_kwargs, messages: List[BaseMessage]
    ) -> Dict:
        try:
            import tiktoken

            # Use cl100k_base encoding which is used by many models
            encoding = tiktoken.get_encoding("cl100k_base")
            max_tokens = 8000  # Maximum tokens per message
        except ImportError:
            logger.warning(
                "tiktoken not installed, token counting disabled. Install with `pip install tiktoken`"
            )
            encoding = None
            max_tokens = float("inf")

        _messages = []
        messages = convert_to_messages(messages)
        for message in messages:
            assert isinstance(
                message, (SystemMessage, HumanMessage, AIMessage, ToolMessage)
            ), message
            content = message.content

            # Truncate content if it exceeds max_tokens
            if encoding and isinstance(content, str) and content:
                tokens = encoding.encode(content)
                if len(tokens) > max_tokens:
                    logger.warning(
                        f"Message content exceeds {max_tokens} tokens, truncating..."
                    )
                    content = encoding.decode(tokens[:max_tokens])

            if isinstance(message, SystemMessage):
                _messages.append({"role": "system", "content": content})
            elif isinstance(message, HumanMessage):
                _messages.append({"role": "user", "content": content})
            elif isinstance(message, AIMessage):
                _messages.append({"role": "assistant", "content": content})
            elif isinstance(message, ToolMessage):
                _messages.append(
                    {
                        "tool_call_id": message.tool_call_id,
                        "role": "tool",
                        "name": message.name,
                        "content": content,
                    }
                )
        return {**model_kwargs, "messages": _messages}


class SageMakerVllmChatModel(_SageMakerVllmChatModel):
    enable_any_tool_choice: bool = False
    any_tool_choice_value: str = "any"
    enable_prefill: bool = True
    is_reasoning_model: bool = False


class SageMakerDeepSeekR1DistillModelBase(ChatModelBase):
    enable_any_tool_choice: bool = False
    any_tool_choice_value: str = "any"
    enable_prefill: bool = True
    is_reasoning_model: bool = False
    default_model_kwargs = {
        "max_tokens": 1000,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    model_provider = ModelProvider.SAGEMAKER

    @classmethod
    def create_model(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs, **model_kwargs}
        print(f"sagemaker model kwargs: {model_kwargs}")
        credentials_profile_name = (
            kwargs.get("credentials_profile_name", None)
            or os.environ.get("AWS_PROFILE", None)
            or None
        )
        region_name = kwargs.get("region_name", None) or current_region
        
        llm = SageMakerVllmChatModel(
            endpoint_name=kwargs["endpoint_name"],
            credentials_profile_name=credentials_profile_name,
            region_name=region_name,
            enable_any_tool_choice=cls.enable_any_tool_choice,
            enable_prefill=cls.enable_prefill,
            is_reasoning_model=cls.is_reasoning_model,
        )
        return llm


class SageMakerDeepSeekR1DistillLlama70B(SageMakerDeepSeekR1DistillModelBase):
    model_id = LLMModelType.DEEPSEEK_R1_DISTILL_LLAMA_70B


class SageMakerDeepSeekR1DistillLlama8B(SageMakerDeepSeekR1DistillModelBase):
    model_id = LLMModelType.DEEPSEEK_R1_DISTILL_LLAMA_8B


class SageMakerDeepSeekR1DistillQwen32B(SageMakerDeepSeekR1DistillModelBase):
    model_id = LLMModelType.DEEPSEEK_R1_DISTILL_QWEN_32B
