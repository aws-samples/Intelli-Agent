import json
import os

os.environ["PYTHONUNBUFFERED"] = "1"
import time
import uuid

import boto3
import utils.parse_config as parse_config
from utils.constant import Type
from utils.ddb_utils import DynamoDBChatMessageHistory
from utils.executor_entries import (
    get_retriever_response,
    main_chain_entry,
    main_qd_retriever_entry,
    main_qq_retriever_entry,
    market_chain_entry,
    market_chain_entry_core,
    market_conversation_summary_entry,
)

# from langchain.retrievers.multi_query import MultiQueryRetriever
from utils.logger_utils import logger
from utils.response_utils import process_response
from utils.serialization_utils import JSONEncoder

# from utils.constant import MKT_CONVERSATION_SUMMARY_TYPE

region = os.environ["AWS_REGION"]
embedding_endpoint = os.environ.get("embedding_endpoint", "")
zh_embedding_endpoint = os.environ.get("zh_embedding_endpoint", "")
en_embedding_endpoint = os.environ.get("en_embedding_endpoint", "")
cross_endpoint = os.environ.get("rerank_endpoint", "")
rerank_endpoint = os.environ.get("rerank_endpoint", "")
aos_endpoint = os.environ.get("aos_endpoint", "")
aos_index = os.environ.get("aos_index", "")
aos_faq_index = os.environ.get("aos_faq_index", "")
aos_ug_index = os.environ.get("aos_ug_index", "")
llm_endpoint = os.environ.get("llm_endpoint", "")
chat_session_table = os.environ.get("chat_session_table", "")
websocket_url = os.environ.get("websocket_url", "")
# sm_client = boto3.client("sagemaker-runtime")
# aos_client = LLMBotOpenSearchClient(aos_endpoint)
ws_client = None


class APIException(Exception):
    def __init__(self, message, code: str = None):
        if code:
            super().__init__("[{}] {}".format(code, message))
        else:
            super().__init__(message)


def load_ws_client():
    global ws_client
    if ws_client is None:
        ws_client = boto3.client("apigatewaymanagementapi", endpoint_url=websocket_url)
    return ws_client


def handle_error(func):
    """Decorator for exception handling"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIException as e:
            logger.exception(e)
            raise e
        except Exception as e:
            logger.exception(e)
            raise RuntimeError(
                "Unknown exception, please check Lambda log for more details"
            )

    return wrapper


def _is_websocket_request(event):
    """Check if the request is WebSocket or Restful

    Args:
        event: lambda request event
    """
    if (
        "requestContext" in event
        and "eventType" in event["requestContext"]
        and event["requestContext"]["eventType"] == "MESSAGE"
    ):
        return True
    else:
        return False


# @handle_error
def lambda_handler(event, context):
    request_timestamp = time.time()
    logger.info(f"request_timestamp :{request_timestamp}")
    logger.info(f"event:{event}")
    logger.info(f"context:{context}")
    if "Records" not in event:
        # Restful API invocation
        event["Records"] = [{"body": json.dumps(event)}]
    for record in event["Records"]:
        record_event = json.loads(record["body"])
        # Get request body
        event_body = json.loads(record_event["body"])
        # model = event_body['model']
        session_id = event_body.get("session_id", None) or "N/A"
        messages = event_body.get("messages", [])

        # deal with stream parameter
        stream = _is_websocket_request(record_event)
        if stream:
            load_ws_client()

        logger.info(f"stream decode: {stream}")
        biz_type = event_body.get("type", Type.COMMON.value)
        client_type = event_body.get("client_type", "default_client_type")
        enable_q_q_match = event_body.get("enable_q_q_match", False)
        enable_debug = event_body.get("enable_debug", False)

        get_contexts = event_body.get("get_contexts", False)

        # all rag related params can be found in rag_config
        rag_config = parse_config.parse_rag_config(event_body)

        debug_level = int(rag_config["debug_level"])
        logger.setLevel(debug_level)

        if messages and biz_type.lower() != Type.MARKET_CONVERSATION_SUMMARY.value:
            assert len(messages) == 1
            question = messages[-1]["content"]
            custom_message_id = messages[-1].get("custom_message_id", None)
        else:
            question = ""  # MARKET_CONVERSATION_SUMMARY
            custom_message_id = None

        # _, question = process_input_messages(messages)
        # role = "user"

        if session_id == "N/A":
            rag_config["session_id"] = f"session_{int(request_timestamp)}"

        if stream:
            rag_config["ws_connection_id"] = record_event["requestContext"][
                "connectionId"
            ]

        user_id = event_body.get("user_id", "default_user_id")
        message_id = str(uuid.uuid4())
        chat_history = DynamoDBChatMessageHistory(
            table_name=chat_session_table,
            session_id=rag_config["session_id"],
            user_id=user_id,
        )
        history_messages = chat_history.message_as_langchain
        rag_config["chat_history"] = history_messages
        logger.info(
            f"rag configs:\n {json.dumps(rag_config,indent=2,ensure_ascii=False,cls=JSONEncoder)}"
        )
        #
        # knowledge_qa_flag = True if model == "knowledge_qa" else False

        main_entry_start = time.time()
        contexts = []
        entry_type = biz_type.lower()
        if entry_type == Type.COMMON.value:
            answer, sources, contexts, debug_info = main_chain_entry(
                question, aos_index, stream=stream, rag_config=rag_config
            )
        elif entry_type == Type.QD_RETRIEVER.value:
            retriever_index = event_body.get("retriever_index", aos_index)
            docs, debug_info = main_qd_retriever_entry(
                question, retriever_index, rag_config=rag_config
            )
            return get_retriever_response(docs, debug_info)
        elif entry_type == Type.QQ_RETRIEVER.value:
            retriever_index = event_body.get("retriever_index", aos_index)
            docs = main_qq_retriever_entry(question, retriever_index)
            return get_retriever_response(docs)
        elif entry_type == Type.DGR.value:
            history = []
            model = event_body.get("model", "chat")
            temperature = event_body.get("temperature", 0.5)
            knowledge_qa_flag = True if model == "knowledge_qa" else False
            answer, sources, contexts, debug_info = dgr_entry(
                session_id,
                question,
                history,
                zh_embedding_endpoint,
                en_embedding_endpoint,
                cross_endpoint,
                rerank_endpoint,
                llm_endpoint,
                aos_faq_index,
                aos_ug_index,
                knowledge_qa_flag,
                temperature,
                enable_q_q_match,
                stream=stream,
            )
        elif entry_type == Type.MARKET_CHAIN_CORE.value:
            answer, sources, contexts, debug_info = market_chain_entry_core(
                question, stream=stream, rag_config=rag_config
            )

        elif entry_type == Type.MARKET_CHAIN.value:
            answer, sources, contexts, debug_info = market_chain_entry(
                question, stream=stream, rag_config=rag_config
            )
        elif entry_type == Type.MARKET_CONVERSATION_SUMMARY.value:
            answer, sources, contexts, debug_info = market_conversation_summary_entry(
                messages=messages, rag_config=rag_config, stream=stream
            )

        main_entry_elpase = time.time() - main_entry_start
        logger.info(f"runing time of {biz_type} entry : {main_entry_elpase}s seconds")

        response_kwargs = dict(
            stream=stream,
            session_id=rag_config["session_id"],
            ws_connection_id=rag_config["ws_connection_id"],
            # model=model,
            entry_type=biz_type.lower(),
            question=question,
            request_timestamp=request_timestamp,
            answer=answer,
            sources=sources,
            get_contexts=get_contexts,
            contexts=contexts,
            enable_debug=enable_debug,
            debug_info=debug_info,
            ws_client=ws_client,
            chat_history=chat_history,
            message_id=message_id,
            client_type=client_type,
            custom_message_id=custom_message_id,
        )
        r = process_response(**response_kwargs)
    if not stream:
        return r
    return {"statusCode": 200, "body": "All records have been processed"}
