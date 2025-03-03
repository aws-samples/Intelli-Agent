import json
import time
import os

import boto3
from common_logic.common_utils.logger_utils import get_logger

logger = get_logger("websocket_utils")

ws_client = None
stop_signals_table_name = os.environ.get("STOP_SIGNALS_TABLE_NAME", "")


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
        ws_client = boto3.client(
            "apigatewaymanagementapi", endpoint_url=websocket_url)
    return ws_client


def send_to_ws_client(message: dict, ws_connection_id):
    ws_client.post_to_connection(
        ConnectionId=ws_connection_id,
        Data=json.dumps(message).encode("utf-8"),
    )


class StopSignalManager:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(stop_signals_table_name)

    def set_stop_signal(self, connection_id: str) -> None:
        """Set stop signal in DynamoDB"""
        try:
            self.table.put_item(
                Item={
                    'wsConnectionId': connection_id,
                    'timestamp': int(time.time()),
                    'ttl': int(time.time() + 600)  # expire after 10 minutes
                }
            )
            logger.info(f"Set stop signal for connection {connection_id}")
        except Exception as e:
            logger.error(f"Failed to set stop signal: {e}")

    def check_stop_signal(self, connection_id: str) -> bool:
        """Check for stop signal in DynamoDB"""
        try:
            response = self.table.get_item(
                Key={'wsConnectionId': connection_id}
            )
            return 'Item' in response
        except Exception as e:
            logger.error(f"Failed to check stop signal: {e}")
            return False

    def clear_stop_signal(self, connection_id: str) -> None:
        """Clear stop signal from DynamoDB"""
        try:
            self.table.delete_item(
                Key={'wsConnectionId': connection_id}
            )
            logger.info(f"Cleared stop signal for connection {connection_id}")
        except Exception as e:
            logger.error(f"Failed to clear stop signal: {e}")


stop_signal_manager = StopSignalManager()


def set_stop_signal(connection_id: str) -> None:
    stop_signal_manager.set_stop_signal(connection_id)


def check_stop_signal(connection_id: str) -> bool:
    return stop_signal_manager.check_stop_signal(connection_id)


def clear_stop_signal(connection_id: str) -> None:
    stop_signal_manager.clear_stop_signal(connection_id)
