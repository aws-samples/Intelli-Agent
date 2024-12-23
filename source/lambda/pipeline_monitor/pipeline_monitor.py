import boto3
import os
import json
import logging
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

region = os.environ.get("AWS_REGION", "us-east-1")
codepipeline = boto3.client("codepipeline", region_name=region)
dynamodb = boto3.client("dynamodb", region_name=region)
model_table_name = os.environ.get("DYNAMODB_TABLE", "")
post_lambda_name = os.environ.get("POST_LAMBDA", "")
CODE_PIPELINE_PREFIX = "DMAA-Env"


def lambda_handler(event, context):
    """
    Custom resource handler to monitor and update CodePipeline
    """
    request_type = event["RequestType"].upper() if (
        "RequestType" in event) else ""
    try:
        logger.info(
            f"Processing {request_type} request with properties: {event.get('ResourceProperties', {})}")

        if event["ResourceType"] == "Custom::CodePipelineMonitor" and \
            ("CREATE" in request_type or "UPDATE" in request_type):
            response = codepipeline.list_pipelines()
            target_pipeline = None

            for pipeline in response["pipelines"]:
                if pipeline["name"].startswith(CODE_PIPELINE_PREFIX):
                    target_pipeline = pipeline["name"]
                    break

            if not target_pipeline:
                logger.warning("No pipeline found starting with DMAA-Env")
                return

            pipeline_response = codepipeline.get_pipeline(name=target_pipeline)
            pipeline_config = pipeline_response["pipeline"]

            # Remove existing monitoring stage if it exists
            pipeline_config["stages"] = [
                stage for stage in pipeline_config["stages"]
                if stage["name"] != "MonitoringStage"
            ]

            # Create new monitoring stage for model deployment pipeline
            monitoring_stage = {
                "name": "MonitoringStage",
                "actions": [{
                    "name": "MonitorAction",
                    "actionTypeId": {
                        "category": "Invoke",
                        "owner": "AWS",
                        "provider": "Lambda",
                        "version": "1"
                    },
                    "configuration": {
                        "FunctionName": post_lambda_name
                    },
                    'outputArtifacts': [],
                    'inputArtifacts': [],
                    "runOrder": 1
                }]
            }

            pipeline_config["stages"].append(monitoring_stage)
            logger.info(pipeline_config)

            codepipeline.update_pipeline(pipeline=pipeline_config)
            logger.info(f"Successfully updated pipeline {target_pipeline}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")


def post_model_deployment(event, context):
    """
    Function to be called by the pipeline monitoring stage
    """
    try:
        logger.info("pipeline completed")
        logger.info(event)
        logger.info(context)
        user_parameters = event["CodePipeline.job"]["data"]["actionConfiguration"]["configuration"]["UserParameters"]
        params = json.loads(user_parameters)
        table_name = params["table"]

        pipeline_name = event["CodePipeline.job"]["data"]["pipelineContext"]["pipelineName"]
        execution_id = event["CodePipeline.job"]["data"]["pipelineContext"]["pipelineExecutionId"]

        response = codepipeline.get_pipeline_execution(
            pipelineName=pipeline_name,
            pipelineExecutionId=execution_id
        )

        status = response["pipelineExecution"]["status"]
        current_time = datetime.datetime.now().isoformat()

        # Write to DynamoDB for any completed status (Succeeded, Failed, etc.)
        if status in ["Succeeded", "Failed", "Stopped"]:
            dynamodb.put_item(
                TableName=table_name,
                Item={
                    "pipelineId": {"S": pipeline_name},
                    "executionId": {"S": execution_id},
                    "status": {"S": status},
                    "timestamp": {"S": current_time},
                    "lastUpdateTime": {"S": current_time}
                }
            )

            logger.info(
                f"Pipeline {pipeline_name} execution {execution_id} completed with status: {status}")
        else:
            logger.info(
                f"Pipeline {pipeline_name} execution {execution_id} is still in progress with status: {status}")

    except Exception as e:
        logger.error(f"Error monitoring pipeline: {str(e)}")
