import os
import traceback
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from shared.constant import EntryType, ParamType, Threshold
from common_logic.common_utils.ddb_utils import DynamoDBChatMessageHistory
from shared.utils.lambda_invoke_utils import (
    chatbot_lambda_call_wrapper,
    is_running_local,
    send_trace
)
from shared.utils.logger_utils import get_logger
from shared.utils.websocket_utils import load_ws_client
from lambda_main.main_utils.online_entries import get_entry
from common_logic.common_utils.response_utils import process_response
from shared.utils.secret_utils import get_secret_value

logger = get_logger("main")

sessions_table_name = os.environ.get("SESSIONS_TABLE_NAME", "")
messages_table_name = os.environ.get("MESSAGES_TABLE_NAME", "")
prompt_table_name = os.environ.get("PROMPT_TABLE_NAME", "")
websocket_url = os.environ.get("WEBSOCKET_URL", "")
openai_key_arn = os.environ.get("OPENAI_KEY_ARN", "")
region_name = os.environ["AWS_REGION"]
session = boto3.session.Session()
secret_manager_client = session.client(
    service_name="secretsmanager", region_name=region_name
)
dynamodb = boto3.resource("dynamodb")
prompt_table = dynamodb.Table(prompt_table_name)
index_table = dynamodb.Table(os.environ.get("INDEX_TABLE_NAME"))
chatbot_table = dynamodb.Table(os.environ.get("CHATBOT_TABLE_NAME"))
model_table = dynamodb.Table(os.environ.get("MODEL_TABLE_NAME"))
embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT")
create_time = str(datetime.now(timezone.utc))
connect_client = boto3.client("connectcases")
connect_domain_id = os.environ.get("CONNECT_DOMAIN_ID", "")
connect_user_arn = os.environ.get("CONNECT_USER_ARN", "")
kb_enabled = os.environ["KNOWLEDGE_BASE_ENABLED"]
kb_type = os.environ["KNOWLEDGE_BASE_TYPE"]


def create_ddb_history_obj(session_id: str, user_id: str, client_type: str, group_name: str, chatbot_id: str) -> DynamoDBChatMessageHistory:
    """Create a DynamoDBChatMessageHistory object

    Args:
        session_id (str): The session id
        user_id (str): The user id
        client_type (str): The client type
        group_name (str): The group name
        chatbot_id (str): The chatbot id

    Returns:
        DynamoDBChatMessageHistory: The DynamoDBChatMessageHistory object
    """
    return DynamoDBChatMessageHistory(
        sessions_table_name=sessions_table_name,
        messages_table_name=messages_table_name,
        session_id=session_id,
        user_id=user_id,
        client_type=client_type,
        group_name=group_name,
        chatbot_id=chatbot_id
    )


def compose_connect_body(event_body: dict, context: dict):
    """
    Compose the body for the Amazon Connect API request based on the event and context.

    Args:
        event_body (dict): The event body received from the Lambda function.
        context (dict): The context object passed to the Lambda function.

    Returns:
        dict: The composed body for the Amazon Connect API request.
    """
    request_timestamp = context["request_timestamp"]
    chatbot_id = os.environ.get("CONNECT_BOT_ID", "admin")
    group_name = os.environ.get("CONNECT_GROUP_NAME", "Admin")
    related_item = event_body["detail"]["relatedItem"]
    case_id = related_item["caseId"]
    logger.info(case_id)

    response = connect_client.get_case(
        caseId=case_id,
        domainId=connect_domain_id,
        fields=[
            {"id": "title"},
            {"id": "summary"},
        ],
    )
    logger.info(response)
    case_fields = response["fields"]
    logger.info(case_fields)
    title, summary = "", ""
    for field in case_fields:
        if field["id"] == "title":
            title = field["value"]["stringValue"]
        if field["id"] == "summary":
            summary = field["value"]["stringValue"]
    query = title + "\n" + summary
    # logger.info("Query:", str(query))
    context_round = event_body.get("context_round", 0)

    # Fix user_id for now
    user_id = event_body.get("user_id", "default_user_id")
    # Use case id for session id
    session_id = case_id

    client_type = event_body.get("client_type", "default_client_type")
    ddb_history_obj = DynamoDBChatMessageHistory(
        sessions_table_name=sessions_table_name,
        messages_table_name=messages_table_name,
        session_id=session_id,
        user_id=user_id,
        client_type=client_type,
        group_name=group_name,
        chatbot_id=chatbot_id
    )
    chat_history = ddb_history_obj.messages_as_langchain

    agent_flow_body = {}
    agent_flow_body["query"] = query
    agent_flow_body["entry_type"] = "common"
    agent_flow_body["user_profile"] = "default"
    agent_flow_body["bot_id"] = chatbot_id
    agent_flow_body["use_history"] = True
    agent_flow_body["enable_trace"] = False
    agent_flow_body["session_id"] = session_id
    # agent_flow_body["chatbot_config"] = get_bot_info(bot_id)
    agent_flow_body["chat_history"] = chat_history
    agent_flow_body["request_timestamp"] = request_timestamp
    agent_flow_body["user_id"] = user_id
    agent_flow_body["message_id"] = str(uuid.uuid4())
    agent_flow_body["context_round"] = context_round
    agent_flow_body["ddb_history_obj"] = ddb_history_obj
    agent_flow_body["stream"] = False
    agent_flow_body["custom_message_id"] = ""
    agent_flow_body["ws_connection_id"] = ""
    agent_flow_body["chatbot_config"] = {
        "chatbot_mode": "agent",
        "group_name": "Admin",
        "chatbot_id": chatbot_id,
        "use_history": True,
        "enable_trace": True,
        "use_websearch": True,
        "default_llm_config": {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "endpoint_name": "",
            "model_kwargs": {"temperature": 0.01, "max_tokens": 1000},
        },
        "agent_config": {"only_use_rag_tool": False},
    }

    logger.info(agent_flow_body)
    return agent_flow_body


def assemble_event_body(event_body: dict, context: dict):
    """
    Assembles the event body for processing based on the provided event body and context.

    This function takes the event body and context as input, extracts relevant information, and constructs a new event body that includes the client type, session ID, user ID, message ID, group name, and chatbot ID. The session ID is generated based on the request timestamp if not provided in the event body.

    Parameters:
        event_body (dict): The original event body received by the lambda function.
        context (dict): The context object provided by the lambda function, containing information such as the request timestamp.

    Returns:
        dict: The assembled event body with the extracted and generated information.
    """
    body = {}
    request_timestamp = context["request_timestamp"]
    body["request_timestamp"] = request_timestamp
    body["client_type"] = event_body.get("client_type", "default_client_type")
    body["session_id"] = event_body.get(
        "session_id", f"session_{int(request_timestamp)}")
    body["user_id"] = event_body.get("user_id", "default_user_id")
    body["message_id"] = event_body.get("custom_message_id", str(uuid.uuid4()))
    body["group_name"] = event_body.get(
        "chatbot_config", {}).get("group_name", "Admin")
    body["chatbot_id"] = event_body.get(
        "chatbot_config", {}).get("chatbot_id", "admin")

    return body


def connect_case_event_handler(event_body: dict, context: dict, executor):
    """
    Handles the event processing for Amazon Connect cases.

    This function processes events related to Amazon Connect cases, specifically handling the creation of case comments. It extracts relevant information from the event body and context, checks the performedBy IAM principal ARN to ensure it's an Amazon Connect service role, and then composes an executor body for further processing. If the check passes, it attempts to execute the executor with the composed body, logs the response message, and adds the response message as a comment to the related case.

    Parameters:
        event_body (dict): The event body received by the lambda function, containing details about the Amazon Connect case event.
        context (dict): The context object provided by the lambda function, containing information such as the request timestamp.
        executor (function): A function that executes the processing of the event, taking the executor body as input.

    Returns:
        dict or str: Returns a dictionary with a status and message indicating the outcome of the processing, or a string indicating an exception has occurred.
    """
    performed_by = event_body["detail"]["performedBy"]["iamPrincipalArn"]
    logger.info(performed_by)
    if "AWSServiceRoleForAmazonConnect" not in performed_by:
        return None

    executor_body = compose_connect_body(event_body, context)
    executor_response: dict = executor(executor_body)
    response_message = executor_response["message"]["content"]
    logger.info(response_message)
    logger.info("Add response message to case comment")

    related_item = event_body["detail"]["relatedItem"]
    case_id = related_item["caseId"]

    response = connect_client.create_related_item(
        caseId=case_id,
        content={
            "comment": {"body": response_message, "contentType": "Text/Plain"},
        },
        domainId=connect_domain_id,
        performedBy={
            "userArn": connect_user_arn,
        },
        type="Comment",
    )
    logger.info(response)

    return {"status": "OK", "message": "Amazon Connect event has been processed"}


def restapi_event_handler(event_body: dict, context: dict, entry_executor):
    """
    Handles the event processing for Restful API requests.

    This function processes events related to Restful API requests, specifically handling the assembly of the event body for further processing. It extracts relevant information from the event body and context, checks the use of history, and then composes a standard event body for further processing. It attempts to execute the entry executor with the composed body, logs the response message, and returns the response.

    Parameters:
        event_body (dict): The event body received by the lambda function, containing details about the Restful API request.
        context (dict): The context object provided by the lambda function, containing information such as the request timestamp.
        entry_executor (function): A function that executes the processing of the event, taking the standard event body as input.

    Returns:
        dict: Returns a dictionary with the response from the entry executor, including the role, content, category, intent_id, and intent_completed.
    """
    assembled_body = assemble_event_body(event_body, context)
    use_history = str(event_body.get("chatbot_config", {}).get(
        "use_history", "true")).lower() == "true"

    ddb_history_obj = create_ddb_history_obj(
        assembled_body["session_id"], assembled_body["user_id"], assembled_body["client_type"], assembled_body["group_name"], assembled_body["chatbot_id"])
    chat_history = ddb_history_obj.messages_as_langchain

    standard_event_body = {
        "query": event_body["query"],
        "entry_type": EntryType.COMMON,
        "session_id": assembled_body["session_id"],
        "user_id": assembled_body["user_id"],
        "chatbot_config": event_body['chatbot_config'],
        "stream": False,
    }

    standard_event_body["chat_history"] = chat_history
    standard_event_body["ddb_history_obj"] = ddb_history_obj
    standard_event_body["request_timestamp"] = assembled_body["request_timestamp"]
    standard_event_body["chatbot_config"]["user_id"] = assembled_body["user_id"]
    standard_event_body["chatbot_config"]["group_name"] = assembled_body["group_name"]
    standard_event_body["chatbot_config"]["chatbot_id"] = assembled_body["chatbot_id"]
    standard_event_body["message_id"] = assembled_body["message_id"]
    standard_event_body["custom_message_id"] = ""
    standard_event_body["ws_connection_id"] = ""

    standard_response = entry_executor(standard_event_body)

    aics_response = {
        "role": standard_response["message"]["role"],
        "content": standard_response["message"]["content"],
        "category": standard_response.get("current_agent_intent_type", ""),
        "intent_id": "i0",
        "intent_completed": "true",
    }

    return aics_response


def default_event_handler(event_body: dict, context: dict, entry_executor):
    """
    Handles the default event (WebSocket API) processing for the lambda function.

    This function is responsible for processing events that do not require special handling, such as those from the WebSocket API. It assembles the event body, loads the WebSocket client, and prepares the DynamoDB history object and chat history for processing. The event body is then passed to the entry executor for further processing.

    Args:
        event_body (dict): The event body received from the Lambda function.
        context (dict): The context object passed to the Lambda function.
        entry_executor (function): A function that executes the processing of the event, taking the standard event body as input.

    Returns:
        dict: Returns a dictionary with the response from the entry executor.
    """
    ws_connection_id = context.get("ws_connection_id")
    assembled_body = assemble_event_body(event_body, context)
    load_ws_client(websocket_url)

    ddb_history_obj = create_ddb_history_obj(
        assembled_body["session_id"], assembled_body["user_id"], assembled_body["client_type"], assembled_body["group_name"], assembled_body["chatbot_id"])
    chat_history = ddb_history_obj.messages_as_langchain

    event_body["stream"] = context["stream"]
    event_body["chat_history"] = chat_history
    event_body["ws_connection_id"] = ws_connection_id
    event_body["custom_message_id"] = assembled_body["message_id"]
    event_body["message_id"] = assembled_body["message_id"]
    event_body["ddb_history_obj"] = ddb_history_obj
    event_body["request_timestamp"] = assembled_body["request_timestamp"]
    event_body["chatbot_config"]["user_id"] = assembled_body["user_id"]
    event_body["chatbot_config"]["group_name"] = assembled_body["group_name"]
    event_body["chatbot_config"]["chatbot_id"] = assembled_body["chatbot_id"]
    event_body["kb_enabled"] = kb_enabled
    event_body["kb_type"] = kb_type

    # Show debug info directly in local mode
    if is_running_local():
        response: dict = entry_executor(event_body)
        return response
    else:
        response: dict = entry_executor(event_body)
        return response


@chatbot_lambda_call_wrapper
def lambda_handler(event_body: dict, context: dict):
    logger.info(f"Raw event_body: {event_body}")
    # set GROUP_NAME for emd model initialize
    os.environ['GROUP_NAME'] = event_body.get(
        "chatbot_config", {}).get("group_name", "Admin")
    param_type = event_body.get("param_type", ParamType.NEST).lower()
    if(param_type == ParamType.FLAT):
        __convert_flat_param_to_dict(event_body)
    entry_type = event_body.get("entry_type", EntryType.COMMON).lower()
    try:
        entry_executor = get_entry(entry_type)
        stream = context["stream"]
        if event_body.get("source", "") == "aws.cases":
            # Amazon Connect case event
            return connect_case_event_handler(event_body, context, entry_executor)
        elif not stream:
            # Restful API
            return restapi_event_handler(event_body, context, entry_executor)
        else:
            # WebSocket API
            return default_event_handler(event_body, context, entry_executor)
    except Exception as e:
        error_response = {"answer": str(e), "extra_response": {}}
        enable_trace = event_body.get(
            "chatbot_config", {}).get("enable_trace", True)
        error_trace = f"\n### Error trace\n\n{traceback.format_exc()}\n\n"
        load_ws_client(websocket_url)
        send_trace(error_trace, enable_trace=enable_trace)
        process_response(event_body, error_response)
        logger.error(f"{traceback.format_exc()}\nAn error occurred: {str(e)}")
        return {"error": str(e)}
    
def __convert_flat_param_to_dict(event_body: dict):
    event_body["chatbot_config"] = event_body.get("chatbot_config", {})
    event_body["chatbot_config"]["max_rounds_in_memory"] = event_body.get("chatbot_max_rounds_in_memory", "")
    event_body["chatbot_config"]["group_name"] = event_body.get("chatbot_group_name", "")
    event_body["chatbot_config"]["chatbot_id"] = event_body.get("chatbot_id", "")
    event_body["chatbot_config"]["goods_id"] = event_body.get("chatbot_goods_id", "")
    event_body["chatbot_config"]["chatbot_mode"] = event_body.get("chatbot_mode", "")
    event_body["chatbot_config"]["use_history"] = event_body.get("chatbot_use_history", True)
    event_body["chatbot_config"]["enable_trace"] = event_body.get("chatbot_enable_trace", True)
    event_body["chatbot_config"]["use_websearch"] = event_body.get("chatbot_use_websearch", False)
    event_body["chatbot_config"]["google_api_key"] = event_body.get("chatbot_google_api_key", "")
    event_body["chatbot_config"]["default_llm_config"] = event_body["chatbot_config"].get("default_llm_config", {})
    event_body["chatbot_config"]["default_llm_config"]["model_id"] = event_body.get("llm_model_id", "")
    event_body["chatbot_config"]["default_llm_config"]["endpoint_name"] = event_body.get("llm_endpoint_name","")
    event_body["chatbot_config"]["model_kwargs"] = event_body["chatbot_config"].get("model_kwargs", {})
    event_body["chatbot_config"]["model_kwargs"]["temperature"] = event_body.get("llm_temperature", Threshold.TEMPERATURE)
    event_body["chatbot_config"]["model_kwargs"]["max_tokens"] = event_body.get("llm_max_tokens", Threshold.MAX_TOKENS)
    event_body["chatbot_config"]["private_knowledge_config"] = event_body["chatbot_config"].get("private_knowledge_config", {})
    event_body["chatbot_config"]["private_knowledge_config"]["top_k"] = event_body.get("private_knowledge_top_k", Threshold.TOP_K_RETRIEVALS)
    event_body["chatbot_config"]["private_knowledge_config"]["score"] = event_body.get("private_knowledge_score", Threshold.ALL_KNOWLEDGE_IN_AGENT_THRESHOLD)
    event_body["chatbot_config"]["agent_config"] = event_body["chatbot_config"].get("agent_config", {})
    event_body["chatbot_config"]["agent_config"]["only_use_rag_tool"] = event_body.get("only_use_rag_tool", True)
