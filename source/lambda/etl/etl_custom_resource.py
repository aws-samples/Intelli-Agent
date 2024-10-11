import logging
import os

import boto3


ENDPOINT_NAME = os.environ["ENDPOINT_NAME"]
VARIANT_NAME = os.environ["VARIANT_NAME"]
logger = logging.getLogger()
logger.setLevel(logging.INFO)
autoscaling_client = boto3.client('application-autoscaling')
cw_client = boto3.client('cloudwatch')


def update_etl_endpoint(endpoint_name, variant_name):
    # This is the format in which application autoscaling references the endpoint
    resource_id = 'endpoint/' + endpoint_name + '/variant/' + variant_name

    step_policy_response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{endpoint_name}-HasBacklogWithoutCapacity-ScalingPolicy",
        # The namespace of the service that provides the resource.
        ServiceNamespace="sagemaker",
        ResourceId=resource_id,
        # SageMaker supports only Instance Count
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="StepScaling",  # 'StepScaling' or 'TargetTrackingScaling'
        StepScalingPolicyConfiguration={
            "AdjustmentType": "ChangeInCapacity",
            # Specifies whether the ScalingAdjustment value in the StepAdjustment property is an absolute number or a
            # percentage of the current capacity.
            # The aggregation type for the CloudWatch metrics.
            "MetricAggregationType": "Average",
            # The amount of time, in seconds, to wait for a previous scaling activity to take effect.
            "Cooldown": 180,
            # A set of adjustments that enable you to scale based on the size of the alarm breach.
            "StepAdjustments":
            [
                {
                    "MetricIntervalLowerBound": 0,
                    "ScalingAdjustment": 1
                }
            ]
        },
    )
    logger.info(f"Put step scaling policy response: {step_policy_response}")

    cw_response = cw_client.put_metric_alarm(
        AlarmName=f'{endpoint_name}-hasbacklogwithoutcapacity-alarm',
        MetricName='HasBacklogWithoutCapacity',
        Namespace='AWS/SageMaker',
        Statistic='Average',
        Period=30,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=1,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        TreatMissingData='missing',
        Dimensions=[
            {'Name': 'EndpointName', 'Value': endpoint_name},
        ],
        AlarmActions=[step_policy_response['PolicyARN']]
    )
    logger.info(f"Put metric alarm response: {step_policy_response}")
    logger.info(
        f"Autoscaling has been enabled for the endpoint: {endpoint_name}")


def lambda_handler(event, context):
    request_type = event["RequestType"].upper() if (
        "RequestType" in event) else ""
    logger.info(request_type)

    # if event["ResourceType"] == "Custom::ETLEndpoint":
    #     if "CREATE" in request_type or "UPDATE" in request_type:
    #         update_etl_endpoint(ENDPOINT_NAME, VARIANT_NAME)
