import os
import traceback
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from common_logic.common_utils.constant import EntryType
from common_logic.common_utils.ddb_utils import DynamoDBChatMessageHistory
from common_logic.common_utils.lambda_invoke_utils import (
    chatbot_lambda_call_wrapper,
    is_running_local,
)
from common_logic.common_utils.logger_utils import get_logger
from common_logic.common_utils.response_utils import process_response
from common_logic.common_utils.websocket_utils import load_ws_client
from lambda_main.main_utils.online_entries import get_entry

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


def get_secret_value(secret_arn: str):
    """Get secret value from secret manager

    Args:
        secret_arn (str): secret arn

    Returns:
        str: secret value
    """
    try:
        get_secret_value_response = secret_manager_client.get_secret_value(
            SecretId=secret_arn
        )
    except ClientError as e:
        raise Exception("Fail to retrieve the secret value: {}".format(e))
    else:
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
            return secret
        else:
            raise Exception("Fail to retrieve the secret value")


def connect_case_event_handler(event_body: dict, context: dict, executor):
    performed_by = event_body["detail"]["performedBy"]["iamPrincipalArn"]
    logger.info(performed_by)
    if "AWSServiceRoleForAmazonConnect" not in performed_by:
        return None

    executor_body = compose_connect_body(event_body, context)

    try:
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
    except Exception as e:
        msg = traceback.format_exc()
        logger.exception("Main exception:%s" % msg)
        return "An exception has occurred, check CloudWatch log for more details"

    return {"status": "OK", "message": "Amazon Connect event has been processed"}


def aics_restapi_event_handler(event_body: dict, context: dict, entry_executor):
    request_timestamp = context["request_timestamp"]
    client_type = event_body.get("client_type", "default_client_type")
    session_id = event_body.get("session_id", f"session_{request_timestamp}")
    user_id = event_body.get("user_id", "default_user_id")
    group_name = event_body.get("group_name", "Admin")
    chatbot_id = event_body.get("chatbot_id", "admin")

    ddb_history_obj = DynamoDBChatMessageHistory(
        sessions_table_name=sessions_table_name,
        messages_table_name=messages_table_name,
        session_id=session_id,
        user_id=user_id,
        client_type=client_type,
    )

    chat_history = ddb_history_obj.messages_as_langchain

    standard_event_body = {
        "query": event_body["query"],
        "entry_type": EntryType.COMMON,
        "session_id": session_id,
        "user_id": user_id,
        "chatbot_config": {
            "chatbot_mode": "agent",
            "use_history": True,
        },
        "stream": False,
    }

    standard_event_body["chat_history"] = chat_history
    standard_event_body["ddb_history_obj"] = ddb_history_obj
    standard_event_body["request_timestamp"] = request_timestamp
    standard_event_body["chatbot_config"]["user_id"] = user_id
    standard_event_body["chatbot_config"]["group_name"] = group_name
    standard_event_body["chatbot_config"]["chatbot_id"] = chatbot_id
    standard_event_body["message_id"] = str(uuid.uuid4())
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


def compose_connect_body(event_body: dict, context: dict):
    request_timestamp = context["request_timestamp"]
    chatbot_id = os.environ.get("CONNECT_BOT_ID", "admin")
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


@chatbot_lambda_call_wrapper
def lambda_handler(event_body: dict, context: dict):
    logger.info(f"raw event_body: {event_body}")
    entry_type = event_body.get("entry_type", EntryType.COMMON).lower()
    entry_executor = get_entry(entry_type)
    stream = context["stream"]
    if event_body.get("source", "") == "aws.cases":
        # Connect case event
        return connect_case_event_handler(event_body, context, entry_executor)
    elif not stream:
        return aics_restapi_event_handler(event_body, context, entry_executor)
    else:

        ws_connection_id = context.get("ws_connection_id")
        request_timestamp = context["request_timestamp"]
        load_ws_client(websocket_url)

        client_type = event_body.get("client_type", "default_client_type")
        session_id = event_body.get("session_id", f"session_{int(request_timestamp)}")
        message_id = event_body.get("custom_message_id", str(uuid.uuid4()))
        user_id = event_body.get("user_id", "default_user_id")
        # TODO Need to modify key
        group_name = event_body.get("chatbot_config", {}).get("group_name", "Admin")
        chatbot_id = event_body.get("chatbot_config", {}).get("chatbot_id", "admin")

        ddb_history_obj = DynamoDBChatMessageHistory(
            sessions_table_name=sessions_table_name,
            messages_table_name=messages_table_name,
            session_id=session_id,
            user_id=user_id,
            client_type=client_type,
        )

        chat_history = ddb_history_obj.messages_as_langchain

        event_body["stream"] = stream
        event_body["chat_history"] = chat_history
        event_body["ws_connection_id"] = ws_connection_id
        event_body["custom_message_id"] = message_id
        event_body["message_id"] = message_id
        event_body["ddb_history_obj"] = ddb_history_obj
        event_body["request_timestamp"] = request_timestamp
        event_body["chatbot_config"]["user_id"] = user_id
        event_body["chatbot_config"]["group_name"] = group_name
        event_body["chatbot_config"]["chatbot_id"] = chatbot_id
        event_body["kb_enabled"] = kb_enabled
        event_body["kb_type"] = kb_type
        # TODO: chatbot id add to event body

        # logger.info(f"event_body:\n{json.dumps(event_body,ensure_ascii=False,indent=2,cls=JSONEncoder)}")
        # debuging
        # show debug info directly in local mode
        if is_running_local():
            response: dict = entry_executor(event_body)
            return response
            # r = process_response(event_body,response)
            # if not stream:
            #     return r
            # return "All records have been processed"
            # return r
        else:
            try:
                response: dict = entry_executor(event_body)
                # r = process_response(event_body,response)
                if not stream:
                    return response
                return "All records have been processed"
            except Exception as e:
                msg = traceback.format_exc()
                logger.exception("Main exception:%s" % msg)
                return "An exception has occurred"
