import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(f"Disconnect: {event}")

    return {"statusCode": 200, "body": json.dumps("Disconnected.")}
