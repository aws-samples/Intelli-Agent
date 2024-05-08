import logging
import os
from datetime import datetime

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()

host_url = os.environ.get("API_GATEWAY_URL")
if not host_url:
    raise Exception("API_GATEWAY_URL is empty")

host_ws_url = os.environ.get("API_GATEWAY_WS_URL")
if not host_ws_url:
    raise Exception("API_GATEWAY_WS_URL is empty")

region_name = host_url.split(".")[2]
if not region_name:
    raise Exception("API_GATEWAY_URL is invalid")

# Remove "/v1" or "/v1/" from the end of the host_url
host_url = host_url.replace("/v1/", "")
host_url = host_url.replace("/v1", "")
if host_url.endswith("/"):
    host_url = host_url[:-1]
logger.info(f"config.host_url: {host_url}")

# Remove "/prod" or "/prod/" from the end of the host_ws_url
host_ws_url = host_ws_url.replace("/prod/", "")
host_ws_url = host_ws_url.replace("/prod", "")
if host_ws_url.endswith("/"):
    host_ws_url = host_ws_url[:-1]
logger.info(f"config.host_ws_url: {host_ws_url}")

api_bucket = os.environ.get("API_BUCKET")
if not api_bucket:
    raise Exception("API_BUCKET is empty")
logger.info(f"config.bucket: {api_bucket}")

test_fast = os.environ.get("TEST_FAST") == "true"
logger.info(f"config.test_fast: {test_fast}")

is_gcr = region_name.startswith("cn-")
logger.info(f"config.is_gcr: {is_gcr}")

endpoint_name = datetime.utcnow().strftime("%m%d%H%M%S")
logger.info(f"config.endpoint_name: {endpoint_name}")

llm_bot_stack = "llm-bot-dev"
