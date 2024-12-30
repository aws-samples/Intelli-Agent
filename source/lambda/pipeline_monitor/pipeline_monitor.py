import boto3
import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

region = os.environ.get("AWS_REGION", "us-east-1")
codepipeline = boto3.client("codepipeline", region_name=region)
dynamodb = boto3.resource("dynamodb")
iam = boto3.client("iam")
model_table_name = os.environ.get("DYNAMODB_TABLE", "")
post_lambda_name = os.environ.get("POST_LAMBDA", "")
CODE_PIPELINE_PREFIX = "DMAA-Env"


def update_pipeline_status(group_name, model_id, new_status):
    table = dynamodb.Table(model_table_name)
    try:
        # Update the status field
        response = table.update_item(
            Key={
                "groupName": group_name,
                "modelId": model_id
            },
            UpdateExpression="SET #status = :status",
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":status": new_status
            },
            ReturnValues="UPDATED_NEW"
        )
        logger.info(response)
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")


def post_model_deployment(event, context):
    """
    Function to be called by the pipeline monitoring stage
    """
    logger.info(event)
    logger.info(context)

    pipeline_name = event["detail"]["pipeline"]
    if not pipeline_name.startswith(CODE_PIPELINE_PREFIX):
        return

    pipeline_state = event["detail"]["state"]
    execution_id = event["detail"]["execution-id"]
    result_map = {
        "SUCCEEDED": "Succeed",
        "FAILED": "Failed",
        "CANCELED": "Failed", 
        "STOPPED": "Failed",
        "SUPERSEDED": "Failed",
        "STARTED": "InProgress",
        "RESUMED": "InProgress",
        "STOPPING": "InProgress"
    }
    logger.info(
        f"Pipeline {pipeline_name} (Execution ID: {execution_id}) is in state: {pipeline_state}")

    pipeline_state = result_map[pipeline_state]
    if pipeline_state in ["Succeed", "Failed"]:
        try:
            execution_details = codepipeline.get_pipeline_execution(
                pipelineName=pipeline_name,
                pipelineExecutionId=execution_id
            )
            logger.info(
                f"Execution details: {json.dumps(execution_details, default=str)}")
            status = execution_details["pipelineExecution"]["status"]
            variables = execution_details["pipelineExecution"]["variables"]
            group_name = None
            model_id = None
            for variable_item in variables:
                if variable_item["name"] == "ModelTag":
                    group_name = variable_item["resolvedValue"]
                elif variable_item["name"] == "ModelId":
                    model_id = variable_item["resolvedValue"]
            
            if group_name is None or model_id is None:
                logger.error(
                    "Unable to find group name or model id in pipeline variables")
                return

            update_pipeline_status(group_name, model_id, status)
        except Exception as e:
            logger.error(f"Error updating pipeline execution details: {str(e)}")



# {"version": "0", "id": "8aeab9d4-d8fe-5ada-fcf1-16b3b4e84648", "detail-type": "CodePipeline Pipeline Execution State Change", "source": "aws.codepipeline", "account": "817734611975", "time": "2024-12-30T00:53:03Z", "region": "us-west-2", "resources": ["arn:aws:codepipeline:us-west-2:817734611975:DMAA-Env-0-4-0-Pipeline"], "detail": {"pipeline": "DMAA-Env-0-4-0-Pipeline", "execution-id": "417b6f73-99ef-4105-95f1-11ebb1bcade5", "start-time": "2024-12-30T00:43:13.765Z", "state": "SUCCEEDED", "version": 6.0, "pipeline-execution-attempt": 1.0}}
