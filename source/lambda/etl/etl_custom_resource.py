import json
import logging
import os

import boto3


ENDPOINT_NAME = os.environ["ENDPOINT_NAME"]
VARIANT_NAME = os.environ["VARIANT_NAME"]

    # autoscaling_client.register_scalable_target(
    #     ServiceNamespace='sagemaker', 
    #     ResourceId=resource_id,
    #     ScalableDimension='sagemaker:variant:DesiredInstanceCount', # The number of EC2 instances for your Amazon SageMaker model endpoint variant.
    #     MinCapacity=0,
    #     MaxCapacity=10
    # )
    # # Define scaling policy
    # response = autoscaling_client.put_scaling_policy(
    #     PolicyName=f"{endpoint_name}-Invocations-ScalingPolicy",
    #     ServiceNamespace="sagemaker",  # The namespace of the AWS service that provides the resource.
    #     ResourceId='endpoint/' + endpoint_name + '/variant/' + variant_name,  # Endpoint name
    #     ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
    #     PolicyType="TargetTrackingScaling",  # 'StepScaling'|'TargetTrackingScaling'
    #     TargetTrackingScalingPolicyConfiguration={
    #         "TargetValue": 3,
    #         # The target value for the metric. - here the metric is - SageMakerVariantInvocationsPerInstance
    #         "CustomizedMetricSpecification": {
    #             "MetricName": "ApproximateBacklogSizePerInstance",
    #             "Namespace": "AWS/SageMaker",
    #             "Dimensions": [{"Name": "EndpointName", "Value": endpoint_name}],
    #             "Statistic": "Average",
    #         },
    #         "ScaleInCooldown": 180,
    #         # The cooldown period helps you prevent your Auto Scaling group from launching or terminating
    #         "ScaleOutCooldown": 60
    #         # ScaleOutCooldown - The amount of time, in seconds, after a scale out activity completes before another
    #         # scale out activity can start.
    #     },
    # )
    # logger.info(f"Put scaling policy response")
    # logger.info(json.dumps(response))
    # alarms = response.get('Alarms')
    # for alarm in alarms:
    #     alarm_name = alarm.get('AlarmName')
    #     logger.info(f"Alarm name: {alarm_name}")
    #     response = cw_client.describe_alarms(
    #         AlarmNames=[alarm_name]
    #     )
    #     logger.info(f"Describe alarm response")
    #     logger.info(response)
    #     comparison_operator = response.get('MetricAlarms')[0]['ComparisonOperator']
    #     if comparison_operator == "LessThanThreshold":
    #         period = 15 * 60  # 15 minutes
    #         evaluation_periods = 4
    #         datapoints_to_alarm = 4
    #         target_value = 1
    #     else:
    #         period = 30
    #         evaluation_periods = 1
    #         datapoints_to_alarm = 1
    #         target_value = 3
    #     response = cw_client.put_metric_alarm(
    #         AlarmName=alarm_name,
    #         Namespace='AWS/SageMaker',
    #         MetricName='ApproximateBacklogSizePerInstance',
    #         Statistic="Average",
    #         Period=period,
    #         EvaluationPeriods=evaluation_periods,
    #         DatapointsToAlarm=datapoints_to_alarm,
    #         Threshold=target_value,
    #         ComparisonOperator=comparison_operator,
    #         AlarmActions=response.get('MetricAlarms')[0]['AlarmActions'],
    #         Dimensions=[{'Name': 'EndpointName', 'Value': endpoint_name}]
    #     )
    #     logger.info(f"Put metric alarm response")
    #     logger.info(response)


logger = logging.getLogger()
logger.setLevel(logging.INFO)
autoscaling_client = boto3.client('application-autoscaling')
cw_client = boto3.client('cloudwatch')


def update_etl_endpoint(endpoint_name, variant_name):
    # This is the format in which application autoscaling references the endpoint
    resource_id = 'endpoint/' + endpoint_name + '/variant/' + variant_name

    step_policy_response = autoscaling_client.put_scaling_policy(
        PolicyName=f"{endpoint_name}-HasBacklogWithoutCapacity-ScalingPolicy",
        ServiceNamespace="sagemaker",  # The namespace of the service that provides the resource.
        ResourceId=resource_id,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",  # SageMaker supports only Instance Count
        PolicyType="StepScaling",  # 'StepScaling' or 'TargetTrackingScaling'
        StepScalingPolicyConfiguration={
            "AdjustmentType": "ChangeInCapacity",
            # Specifies whether the ScalingAdjustment value in the StepAdjustment property is an absolute number or a
            # percentage of the current capacity.
            "MetricAggregationType": "Average",  # The aggregation type for the CloudWatch metrics.
            "Cooldown": 180,  # The amount of time, in seconds, to wait for a previous scaling activity to take effect.
            "StepAdjustments":  # A set of adjustments that enable you to scale based on the size of the alarm breach.
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

    logger.info(f"Autoscaling has been enabled for the endpoint: {endpoint_name}")
    logger.info("cw alarm response")
    logger.info(cw_response)


def lambda_handler(event, context):
    request_type = event["RequestType"].upper() if (
        "RequestType" in event) else ""
    logger.info(request_type)

    if event["ResourceType"] == "Custom::ETLEndpoint":
        if "CREATE" in request_type or "UPDATE" in request_type:
            update_etl_endpoint(ENDPOINT_NAME, VARIANT_NAME)
