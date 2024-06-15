
import json
from typing import Union,Optional, Union
import os
import boto3
import requests
from pydantic import BaseModel,ValidationInfo, field_validator, Field
import re

def get_all_regions():
    ec2 = boto3.client('ec2')
    regions = ec2.describe_regions()
    return [region['RegionName'] for region in regions['Regions']] + ['cn-north-1', 'cn-northwest-1']

def get_all_services():
    session = boto3.Session()
    services = session.get_available_services()
    return services

class ServiceAvailabilityRequest(BaseModel):
    region: str = Field (description='region name')
    service: str = Field (description='service name')

    # def __init__(self, **data):
    #     super().__init__(**data)
    #     self.region = self.region.lower()
    #     self.service = self.service.lower()
    
    @field_validator('region')
    @classmethod
    def validate_region(cls, region):
        if region not in region_list:
            raise ValueError("region must be in aws region list.")
        return region

    @field_validator('service')
    @classmethod
    def validate_service(cls, service):
        if service not in service_list:
            raise ValueError("service must be in aws service list.")
        return service

region_list = get_all_regions()
service_list = get_all_services()

def check_service_availability(args):
    try:
        request = ServiceAvailabilityRequest(**args)
    except Exception as e:
        return str(e)
    service = request.service
    region = request.region
    try:
        # Attempt to create a client for the specified service in the specified region
        boto3.client(service, region_name=region)
        return "available"
    except Exception as e:
        # Handle exceptions, which may indicate that the service is not available in the region
        print(f"Service {service} is not available in {region}: {e}")
        return "unavailable"
    
def lambda_handler(event, context=None):
    '''
    event: {
        "body": "{
            \"instance_type\":\"m5.xlarge\",
            \"region\":\"us-east-1\",
            \"term\":\"eserved\",
            \"purchase_option\":\"All Upfront\"
        }"
    }
    '''
    result = check_service_availability(event)
    return {"code":0, "result": result}

if __name__ == "__main__":
    # Example usage
    args = {'service':'bedrock','region':'cn-north-1'}
    is_available = check_service_availability(args)
    print(f'Service {args["service"]} is available in {args["region"]}: {is_available}')