from common_logic.common_utils.constant import SceneType,ToolRuningMode
from .._tool_base import tool_manager 
from . import (
    check_service_availability,
    explain_abbr,
    service_org,
    aws_ec2_price

)

SCENE = SceneType.AWS_QA
LAMBDA_NAME = "lambda_aws_qa_tools"

tool_manager.register_tool({
    "name": "service_availability",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": check_service_availability.lambda_handler,
    "tool_def":{
        "name": "service_availability",
        "description":"query the availability of service in specified region",
        "parameters":{
            "type":"object",
            "properties":{
                "service":{
                    "type":"string",
                    "description":"the AWS service name"
                },
                "region":{
                    "type":"string",
                    "description":"the AWS region name where the service is located in, for example us-east-1(N.Virginal), us-west-2(Oregon), eu-west-2(London), ap-southeast-1(Singapore)"
                }
            },
            "required":[
                "service",
                "region"
            ]
        },
        "running_mode": ToolRuningMode.LOOP
    }
})

tool_manager.register_tool({
    "name": "explain_abbr",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": explain_abbr.lambda_handler,
    "tool_def":{
        "name": "explain_abbr",
        "description": "explain abbreviation for user",
        "parameters": {
            "type": "object",
            "properties": {
                "abbr": {
                    "type": "string",
                    "description": "the abbreviation of terms in AWS"
                }
            },
            "required": ["abbr"]
        },
        "running_mode": ToolRuningMode.ONCE
    }
})


tool_manager.register_tool({
    "name": "get_contact",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": service_org.lambda_handler,
    "tool_def":{
        "name":"get_contact",
        "description":"query the contact person in the 'SSO' organization",
        "parameters":{
            "type":"object",
            "properties":{
                "employee":{
                    "type":"string",
                    "description":"employee name in the 'SSO' organization"
                },
                "role":{
                    "type":"string",
                    "description":"employee's role, usually it's Sales, Product Manager, Tech, Program Manager, Leader"
                },
                "domain":{
                    "type":"string",
                    "description":"Techical domain for the employee，For Example AIML, Analytics, Compute"
                },
                "scope":{
                    "type":"string",
                    "description":"employee's scope of responsibility. For Sales role, it could be territory like north/east/south/west, For tech role, it could be specific service"
                }
            },
            "required":[
                "employee"
            ]
        },
        "running_mode": ToolRuningMode.LOOP
     }
})

tool_manager.register_tool({
    "name": "ec2_price",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": aws_ec2_price.lambda_handler,
    "tool_def": {
        "name": "ec2_price",
        "description": "query the price of AWS ec2 instance",
        "parameters": {
            "type": "object",
            "properties": {
                "instance_type": {
                    "type": "string",
                    "description": "the AWS ec2 instance type, for example, c5.xlarge, m5.large, t3.mirco, g4dn.2xlarge, if it is a partial of the instance type, you should try to auto complete it. for example, if it is r6g.2x, you can complete it as r6g.2xlarge"
                },
                "region": {
                    "type": "string",
                    "description": "the AWS region name where the ec2 is located in, for example us-east-1, us-west-1, if it is common words such as 'us east 1','美东1','美西2',you should try to normalize it to standard AWS region name, for example, 'us east 1' is normalized to 'us-east-1', '美东2' is normalized to 'us-east-2','美西2' is normalized to 'us-west-2','北京' is normalized to 'cn-north-1', '宁夏' is normalized to 'cn-northwest-1', '中国区' is normalized to 'cn-north-1'"
                },
                "os": {
                    "type": "string",
                    "description": "the operating system of ec2 instance, the valid value should be 'Linux' or 'Windows'"
                },
                "term": {
                    "type": "string",
                    "description": "the payment term, the valid value should be 'OnDemand' or 'Reserved' "
                },
                "purchase_option": {
                    "type": "string",
                    "description": "the purchase option of Reserved instance, the valid value should be 'No Upfront', 'Partial Upfront' or 'All Upfront' "
                }
            },
            "required": ["instance_type"]
        },
        "running_mode": ToolRuningMode.LOOP
    }
})

# tool_manager.register_tool({
#     "name":"assist",
#     "lambda_name": "",
#     "lambda_module_path": "",
#     "tool_def": {
#         "name": "assist",
#         "description": "assist user to do some office work",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "response": {
#                     "description": "Response to user",
#                     "type": "string"
#             }
#             },
#             "required": ["response"]
#         },
#     },
#     "running_mode":ToolRuningMode.ONCE
# })





