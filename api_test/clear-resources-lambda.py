import json
import boto3
import re
import logging
from botocore.exceptions import ClientError

logger=logging.getLogger(__name__)
ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    '''lambda_handler'''
    if event['error_msg'].startswith("The subnet "):
        __delete_subnet(re.search(r"'(.*?)'", event['error_msg']).group(1))
    else:
        logger.error("invalid Parameter!!!")

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def __delete_subnet(subnet_id):
    try:
        response = ec2_client.describe_network_interfaces(Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}])
        for eni in response['NetworkInterfaces']:
            ec2_client.delete_network_interface(NetworkInterfaceId=eni['NetworkInterfaceId'])
            logger.info("!!!!!%s is deleted!!!!!", eni['NetworkInterfaceId'])
        ec2_client.delete_subnet(SubnetId=subnet_id)
    except ClientError as e:
        logger.error("Error in deleting subnet: %s", e)
