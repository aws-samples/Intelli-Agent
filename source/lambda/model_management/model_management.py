import json
import os
import time
import boto3
from datetime import datetime, timezone 
from dmaa import deploy,destroy
from dmaa.models import Model
import botocore
from dmaa.sdk.status import get_model_status
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
region = boto3.Session().region_name

ROOT_RESOURCE = "/model-management"
DEPLOY_RESOURCE = f"{ROOT_RESOURCE}/deploy"
DESTROY_RESOURCE = f"{ROOT_RESOURCE}/destroy"
STATUS_RESOURCE = f"{ROOT_RESOURCE}/status"

# status
DELETING = "DELETING"
DEPLOYING = "DEPLOYING"
READY_FOR_DEPLOYMENT = "READY_FOR_DEPLOYMENT"


dynamodb_resource = boto3.resource("dynamodb")
model_table_name = os.getenv("MODEL_TABLE_NAME","model-management")
assert model_table_name,model_table_name

model_table = dynamodb_resource.Table(model_table_name)

resp_header = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
}

def get_query_parameter(event, parameter_name, default_value=None):
    if (
        event.get("queryStringParameters")
        and parameter_name in event["queryStringParameters"]
    ):
        return event["queryStringParameters"][parameter_name]
    return default_value


def get_model_item(group_name,model_id):
    response = model_table.get_item(Key={"groupName": group_name, "modelId": model_id})
    item = response.get("Item",{})
    now_time_str = get_now_time()
    cur_item = {
            "groupName": group_name,
            "modelId": model_id,
            "createTime": now_time_str,
            "parameter":{},
            "modelType": "LLM"
    }
    item = {
            **cur_item,
            **item
        }
    item['updateTime'] = now_time_str
    return item 


def get_sort_key(model_id,model_tag):
    return f"{model_id}__{model_tag}"


def get_now_time():
    now = datetime.now(timezone.utc)
    formatted_time = now.isoformat()
    return formatted_time

def __deploy(event,group_name):
    body = json.loads(event["body"])
    model_id = body["model_id"]
    model = Model.get_model(model_id)
    instance_type = body.get('instance_type')
    if not instance_type:
        instance_type = model.supported_instances[0].instance_type
    
    service_type = body.get('service_type')
    if not service_type:
        service_type = model.supported_services[0].service_type
    
    engine_type = body.get('engine_type')
    if not engine_type:
        engine_type = model.supported_engines[0].engine_type
    
    framework_type = body.get("framework_type")
    if not framework_type:
        framework_type = model.supported_frameworks[0].framework_type
    
    extra_params = body.get("extra_params")
    model_tag=group_name
    ret = deploy(
        model_id=model_id,
        instance_type=instance_type,
        engine_type=engine_type,
        service_type=service_type,
        framework_type=framework_type,
        region=region,
        extra_params=extra_params,
        model_tag=model_tag,
        waiting_until_deploy_complete=False
    )
    ret['model_tag'] = model_tag
    logger.info(f'deploy ret: {ret}')
    # write ret to ddb 
    now_time_str = get_now_time()
    item = get_model_item(group_name,model_id)
    ret['model_deploy_start_time'] = f"{ret['model_deploy_start_time']}"
    item['status'] = DEPLOYING
    # item = {
    #         "groupName": group_name,
    #         "modelId": model_id,
    #         "createTime": now_time_str,
    #         "modelType": "LLM",
    #         "parameter":ret,
    #         "status": "InProgress",
    #         "updateTime": now_time_str
    #     }
    model_table.put_item(
        Item=item
    )
    return item
    

def __destroy(event, group_name):
    body = json.loads(event["body"])
    model_id = body["model_id"]
    item = get_model_item(group_name,model_id)
    ret = get_model_status(model_id,model_tag=group_name)
    inprogress = ret['inprogress']
    completed = ret['completed']
    if not inprogress and not completed:
        item['status'] = "deleted"
        model_table.put_item(
            Item=item
        )
        return item 

    destroy(
        model_id=model_id,
        model_tag=group_name,
        waiting_until_complete=False
    )
    item['status'] = DELETING

    model_table.put_item(
        Item=item
    )
    return item

def __status(event, group_name):
    body = json.loads(event["body"])
    model_id = body["model_id"]
    # sort_key = get_sort_key(model_id,group_name)
    
    ret = get_model_status(model_id,model_tag=group_name)

    inprogress = ret['inprogress']
    completed = ret['completed']
    if inprogress:
        status = f"Deploy {inprogress[0]['status']} ({inprogress[0]['stage_name']})"
    elif completed:
        status = completed[0]['stack_status']
    else:
        return {
            "groupName":group_name,
            "modeId":model_id,
            'status':READY_FOR_DEPLOYMENT,"info":"model not exists "
        }
     
    item = get_model_item(group_name,model_id)
    item['status'] = status
    model_table.put_item(
        Item=item
    )
    return item


api_map = {
    DEPLOY_RESOURCE: __deploy,
    DESTROY_RESOURCE: __destroy,
    STATUS_RESOURCE: __status,
}


def lambda_handler(event, context):
    logger.info(f"event: {event}")
    group_name = get_query_parameter(event, "GroupName", "Admin")
    # authorizer_type = (
    #     event["requestContext"].get("authorizer", {}).get("authorizerType")
    # )
    # if authorizer_type == "lambda_authorizer":
    #     claims = json.loads(event["requestContext"]["authorizer"]["claims"])
    #     if "use_api_key" in claims:
    #         group_name = get_query_parameter(event, "GroupName", "Admin")
    #     else:
    #         group_name = claims["cognito:groups"]
    # else:
    #     logger.error("Invalid authorizer type")
    #     return {
    #         "statusCode": 403,
    #         "headers": resp_header,
    #         "body": json.dumps({"error": "Invalid authorizer type"}),
    #     }
    http_method = event["httpMethod"]
    resource: str = event["resource"]

    try:
        output = api_map[resource](event,group_name)
        return {
            "statusCode": 200,
            "headers": resp_header,
            "body": json.dumps(output),
        }
    except Exception as e:
        logger.error("Error: %s", str(e))
        import traceback 
        trace_error = traceback.format_exc()
        return {
            "statusCode": 500,
            "headers": resp_header,
            "body": json.dumps(f"Error: {str(trace_error)}"),
        }
