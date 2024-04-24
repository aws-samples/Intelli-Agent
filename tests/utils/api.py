import json
import logging

import requests
from jsonschema.validators import validate
from websocket import WebSocket

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Api:
    schema = None

    def __init__(self, config):
        self.config = config

    def req(
        self,
        method: str,
        path: str,
        operation_id: str = None,
        headers=None,
        data=None,
        params=None,
    ):

        if data is not None:
            data = json.dumps(data)

        url = f"{self.config.host_url}/v1/{path}"

        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            params=params,
            timeout=(30, 40),
        )

        dump_string = ""
        if headers:
            dump_string += f"\nRequest headers: {get_json(headers)}"
        if data:
            dump_string += f"\nRequest data: {get_json(data)}"
        if params:
            dump_string += f"\nRequest params: {get_json(params)}"
        if resp.status_code:
            dump_string += f"\nResponse status_code: {resp.status_code}"
        if resp.text:
            dump_string += f"\nResponse body: {get_json(resp.text)}"

        resp.dumps = lambda: logger.info(
            "\n----------------------------"
            "\n%s %s"
            "%s"
            "\n----------------------------",
            method,
            url,
            dump_string,
        )

        if operation_id:
            validate_response(self, resp, operation_id)

        return resp

    def qa(self, headers=None, data=None):
        return self.req(
            method="POST",
            path="llm",
            operation_id="get_llm_response",
            headers=headers,
            data=data,
        )

    def trigger_etl(self, headers=None, data=None):
        return self.req(
            method="POST",
            path="etl",
            operation_id="trigger_etl",
            headers=headers,
            data=data,
        )

    def get_etl_status(self, headers=None, params=None):
        return self.req(
            method="GET",
            path="etl/status",
            operation_id="get_etl_status",
            headers=headers,
            params=params,
        )

    def query_aos_index(self, headers=None, params=None, data=None):
        return self.req(
            method="GET",
            path="aos",
            operation_id="query_aos_index",
            headers=headers,
            params=params,
            data=data,
        )


class WsApi:
    schema = None

    def __init__(self, config):
        self.config = config

    def qa(
        self,
        operation_id: str = None,
        headers=None,
        data=None,
        params=None,
    ):
        ws_url = f"{self.config.host_ws_url}/prod/"
        ws_client = WebSocket()
        ws_client.connect(ws_url, timeout=15)
        ws_client.send(json.dumps(data))
        answer = ""
        context = ""

        while True:
            try:
                ret = json.loads(ws_client.recv())
                message_type = ret["choices"][0]["message_type"]
            except Exception as e:
                break
            if message_type == "START":
                continue
            elif message_type == "CHUNK":
                answer += ret["choices"][0]["message"]["content"]
            elif message_type == "END":
                break
            elif message_type == "ERROR":
                break
            elif message_type == "CONTEXT":
                message = ret["choices"][0]
                if "_chunk_data" in message:
                    context += message.pop("_chunk_data")
                    if message["chunk_id"] + 1 != message["total_chunk_num"]:
                        continue
                    message.update(json.loads(context))
                    context = message
                context = ret

        ws_client.close()

        # if operation_id:
        #     validate_response(self, resp, operation_id)

        return answer, context


def get_schema_by_id_and_code(api: Api, operation_id: str, code: int):
    code = str(code)

    responses = None
    for path, methods in api.schema["paths"].items():
        for method, op in methods.items():
            if op.get("operationId") == operation_id:
                responses = op["responses"]
                break

    if responses is None:
        raise Exception(f"{operation_id} not found")

    if f"{code}" not in responses:
        raise Exception(f"{code} not found in responses of {operation_id}")

    ref = responses[f"{code}"]["content"]["application/json"]["schema"]["$ref"]
    model_name = ref.split("/")[-1]
    json_schema = api.schema["components"]["schemas"][model_name]

    return json_schema


def validate_response(api: Api, resp: requests.Response, operation_id: str):
    if resp.status_code in [200, 204]:
        return
    else:
        with open("response.json", "w") as s:
            s.write(json.dumps(resp.json(), indent=4))

        validate_schema = get_schema_by_id_and_code(api, operation_id, resp.status_code)

        try:
            validate(instance=resp.json(), schema=validate_schema)
        except Exception as e:
            print("\n**********************************************")
            with open("schema.json", "w") as s:
                s.write(json.dumps(validate_schema, indent=4))
            print("\n**********************************************")
            print(operation_id)
            print("\n**********************************************")
            raise e


def get_json(data):
    try:
        # if data is string
        if isinstance(data, str):
            return json.dumps(json.loads(data), indent=4)
        # if data is object
        if isinstance(data, dict):
            json.dumps(dict(data), indent=4)
        return str(data)
    except TypeError:
        return str(data)
