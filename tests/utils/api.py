import json
import logging

import requests
from jsonschema.validators import validate

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
        print(url)

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
        with open(f"response.json", "w") as s:
            s.write(json.dumps(resp.json(), indent=4))

        validate_schema = get_schema_by_id_and_code(api, operation_id, resp.status_code)

        try:
            validate(instance=resp.json(), schema=validate_schema)
        except Exception as e:
            print(f"\n**********************************************")
            with open(f"schema.json", "w") as s:
                s.write(json.dumps(validate_schema, indent=4))
            print(f"\n**********************************************")
            print(operation_id)
            print(f"\n**********************************************")
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
