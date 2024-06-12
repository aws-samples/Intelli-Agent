
import json
from typing import Any, Dict, List, Union,Mapping, Optional, TypeVar, Union
import os
import boto3
import requests
from pydantic import BaseModel,ValidationInfo, field_validator, Field,ValidationError
import re

class EC2PriceRequest(BaseModel):
    region: Optional[str] = Field (description='region name', default='us-east-1')
    term: Optional[str] = Field (description='purchase term', default='OnDemand')
    instance_type: str 
    purchase_option: Optional[str] = Field (description='purchase option', default='')
    os:Optional[str] = Field(description='Operation system', default='Linux')

    @classmethod
    def validate_ec2_instance_type(cls,instance_type):
        # support other instance ml.m5.xlarge
        # pattern = r'^(?:[a-z0-9][a-z0-9.-]*[a-z0-9])?(?:[a-z](?:[a-z0-9-]*[a-z0-9])?)?(\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z0-9]{2,63}$'
        ## only ec2, for m5.xlarge
        pattern = r"^([a-z0-9]+\.[a-z0-9]+)$"

        return re.match(pattern, instance_type) is not None and not instance_type.endswith(".")
    
    @classmethod
    def validate_region_name(cls,region_name):
        pattern = r"^[a-z]{2}(-gov)?-(central|east|north|south|west|northeast|northwest|southeast|southwest)-\d$"
        return re.match(pattern, region_name) is not None

    @field_validator('region')
    def validate_region(cls, value:str,info: ValidationInfo):
        if not cls.validate_region_name(value):
            raise ValueError(f"{value} is not a valid AWS region name.")
        return value
    
    @field_validator('term')
    def validate_term(cls, value:str,info: ValidationInfo):
        allowed_values = ['OnDemand','Reserved']
        if value not in allowed_values:
            raise ValueError(f'value must be one of {allowed_values}')
        return value
    
    @field_validator('purchase_option')
    def validate_option(cls, value:str,info: ValidationInfo):
        allowed_values = ['No Upfront','All Upfront','Partial Upfront','']
        if value not in allowed_values:
            raise ValueError(f'value must be one of {allowed_values}')
        return value

    @field_validator('os')
    def validate_os(cls, value:str,info: ValidationInfo):
        allowed_values = ['Linux','Windows']
        if value not in allowed_values:
            raise ValueError(f'value must be one of {allowed_values}')
        return value

    @field_validator('instance_type')
    def validate_instance_type(cls, value:str,info: ValidationInfo):
        if not cls.validate_ec2_instance_type(value):
            raise ValueError(f'{value} is not a valid EC2 instance type name.')
        return value

def purchase_option_filter(term_attri:dict, value:str) -> dict:
    if not value:
        return True
    if term_attri:
        purchaseOption = term_attri.get('PurchaseOption')
        if purchaseOption == value:
            return True
    return None


def remote_proxy_call(**args):
    api = os.environ.get('api_endpoint')
    key = os.environ.get('api_key')
    payload = json.dumps(args)
    if not api or not key:
        return None
    try:
        resp = requests.post(api,headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"},data=payload)
        data = resp.json()
        return data.get('message')
    except Exception as e:
        print(e)
        return None
    

def query_ec2_price(**args) -> Union[str,None]:  
    request = EC2PriceRequest(**args)
    region = request.region
    term = request.term
    instance_type = request.instance_type
    os = request.os
    purchase_option = request.purchase_option
    if region.startswith('cn-'):
        return remote_proxy_call(**args)
    else:
        pricing_client = boto3.client('pricing',region_name='us-east-1')
        def parse_price(products,term):
            ret = []
            for product in products:
                product = json.loads(product)
                on_demand_terms = product['terms'].get(term)
                if on_demand_terms and term == 'Reserved':
                    for _, term_details in on_demand_terms.items():
                        price_dimensions = term_details['priceDimensions']
                        term_attri = term_details.get('termAttributes')
                        is_valid = purchase_option_filter(term_attri,purchase_option)
                        option = term_attri.get('PurchaseOption')
                        if is_valid:
                            for _, price_dimension in price_dimensions.items():
                                price = price_dimension['pricePerUnit']['CNY'] if region.startswith('cn-') else price_dimension['pricePerUnit']['USD']
                                dollar = 'CNY' if region.startswith('cn-') else 'USD'
                                desc =  price_dimension['description']
                                unit =  price_dimension['unit']
                                if not desc.startswith("$0.00 per") and not desc.startswith("USD 0.0 per") \
                                        and not desc.startswith("0.00 CNY per") and not desc.startswith("CNY 0.0 per"):
                                    ret.append(f"Region: {region}, Purchase option: {option}, Lease contract length: {term_attri.get('LeaseContractLength')}, Offering Class: {term_attri.get('OfferingClass')}, Price per {unit}: {dollar} {price} , description: {desc}")
                elif on_demand_terms:
                    for _, term_details in on_demand_terms.items():
                        price_dimensions = term_details['priceDimensions']
                        if price_dimensions:
                            for _, price_dimension in price_dimensions.items():
                                price = price_dimension['pricePerUnit']['CNY'] if region.startswith('cn-') else price_dimension['pricePerUnit']['USD']
                                desc =  price_dimension['description']
                                unit =  price_dimension['unit']
                                if not desc.startswith("$0.00 per") and not desc.startswith("USD 0.0 per") and not desc.startswith("0.00 CNY per"):
                                    ret.append(f"Region: {region}, Price per {unit}: {price}, description: {desc}")
            return ret
        filters = [
            {
                'Type': 'TERM_MATCH',
                'Field': 'instanceType',
                'Value': instance_type 
            },
            {
                'Type': 'TERM_MATCH',
                'Field': 'ServiceCode',
                'Value': 'AmazonEC2'
            },
            {
                'Type': 'TERM_MATCH',
                'Field': 'regionCode',
                'Value': region
            },
            {
                'Type': 'TERM_MATCH',
                'Field': 'tenancy',
                'Value': 'Shared'
            },
            {
                'Type': 'TERM_MATCH',
                'Field': 'operatingSystem',
                'Value': os
            }
        ]
    
        if purchase_option:
            filters = filters + [{
                        'Type': 'TERM_MATCH',
                        'Field': 'PurchaseOption',
                        'Value': purchase_option
                    }] 
            
        response = pricing_client.get_products(
            ServiceCode='AmazonEC2',
            Filters=filters
        )
        products = response['PriceList']
        prices = parse_price(products,term)
        
        return '\n'.join(prices) if prices else None

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
    result = query_ec2_price(**event)
    return {"code":0, "result": result}

if __name__ == "__main__":
    args = {'instance_type':'m5.xlarge','region':'us-east-1','term':'Reserved','purchase_option':'All Upfront'}
    print(query_ec2_price(**args))