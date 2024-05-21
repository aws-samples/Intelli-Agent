import boto3 
import json 
from common_utils.logger_utils import get_logger

logger = get_logger("websocket_utils")

ws_client = None 

class WebsocketClientError(Exception):
    pass

def is_websocket_request(event):
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


def load_ws_client(websocket_url):
    global ws_client
    if ws_client is None:
        ws_client = boto3.client("apigatewaymanagementapi", endpoint_url=websocket_url)
    return ws_client


def send_to_ws_client(message: dict,ws_connection_id):
    ws_client.post_to_connection(
        ConnectionId=ws_connection_id,
        Data=json.dumps(message).encode("utf-8"),
    )

    # data_to_send = json.dumps(message).encode("utf-8")
    # logger.info(
    #     f"Send to ws client error occurs, the message to send is: {data_to_send}"
    # )








