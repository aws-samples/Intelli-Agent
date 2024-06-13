from langchain.pydantic_v1 import BaseModel,Field
from enum import Enum

class ToolDefType(Enum):
    openai = "openai"

class Tool(BaseModel):
    name: str = Field(description="tool name")
    lambda_name: str = Field(description="lambda name")
    lambda_module_path: str = Field(description="local module path")
    handler_name:str = Field(description="local handler name", default="lambda_handler")
    tool_def: dict = Field(description="tool definition")
    tool_def_type: ToolDefType = Field(description="tool definition type",default=ToolDefType.openai.value)
    

class ToolManager:
    def __init__(self) -> None:
        self.tools = {}
    
    def register_tool(self,tool_info:dict):
        tool_def = tool_info['tool_def']
        if "parameters" not in tool_def:
            tool_def['parameters'] = {
                "type": "object",
                "properties": {},
                "required": []
            }

        tool = Tool(**tool_info)
        assert tool.tool_def_type == ToolDefType.openai.value, f"tool_def_type: {tool.tool_def_type} not support"
        self.tools[tool.name] = tool

    def get_tool_by_name(self,name):
        return self.tools[name]

tool_manager = ToolManager()
get_tool_by_name = tool_manager.get_tool_by_name

tool_manager.register_tool({
    "name": "get_weather",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.lambda_get_weather.get_weather",
    "tool_def":{
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                "location": {
                    "description": "The city and state, e.g. San Francisco, CA",
                    "type": "string"
                },
                "unit": {
                    "description": "The unit of temperature",
                    "allOf": [
                    {
                        "title": "Unit",
                        "description": "An enumeration.",
                        "enum": [
                        "celsius",
                        "fahrenheit"
                        ]
                    }
                    ]
                }
                },
                "required": [
                "location",
                "unit"
                ]
            }
        }
    }
)


tool_manager.register_tool(
    {
        "name":"give_rhetorical_question",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.lambda_give_rhetorical_question.give_rhetorical_question",
        "tool_def":{
                "name": "give_rhetorical_question",
                "description": "If the user's question is not clear and specific, resulting in the inability to call other tools, please call this tool to ask the user a rhetorical question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "description": "Rhetorical questions for users",
                            "type": "string"
                    }
                },
                "required": ["question"]
            }
        }
    }
)


tool_manager.register_tool(
    {
        "name":"no_available_tool",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.lambda_no_available_tool.no_available_tool",
        "tool_def":{
                "name": "no_available_tool",
                "description": "If you find some tools are not available, call this tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "description": "Response to user that no relevant tool exists to answer the question at hand",
                            "type": "string"
                    }
                },
                "required": ["response"]
            }
        }
    }
)


tool_manager.register_tool(
    {
        "name": "give_final_response",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.lambda_give_final_response.give_final_response",
        "tool_def":{
                "name": "give_final_response",
                "description": "If none of the other tools need to be called, call the current tool to complete the direct response to the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "description": "Response to user",
                            "type": "string"
                    }
                },
                "required": ["response"]
            }
        }
    }
)

tool_manager.register_tool(
    {
        "name":"search_lihoyo",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.lambda_retriever.retriever",
        "tool_def":{
                "name": "search_lihoyo",
                "description": "Retrieve knowledge about lihoyo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "description": "query to retrieve",
                            "type": "string"
                    }
                },
                "required": ["query"]
            }
        }
    }
)



##### default tools #########
tool_manager.register_tool({
    "name": "service_availability",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
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
        }
    }
})


tool_manager.register_tool({
    "name": "explain_abbr",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
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
        }
    }
})

tool_manager.register_tool({
    "name": "get_contact",
    "lambda_name": "service_org",
    "lambda_module_path": "functions.lambda_service_org.service_org",
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
        }
     }
})

tool_manager.register_tool({
    "name": "ec2_price",
    "lambda_name": "ec2_price",
    "lambda_module_path": "functions.lambda_aws_api.aws_api",
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
        }
    }
})

tool_manager.register_tool({
    "name":"assist",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "assist",
        "description": "assist user to do some office work"
    }
})

tool_manager.register_tool({
    "name":"QA",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "QA",
        "description": "answer question according to searched relevant content"
    }
})

tool_manager.register_tool({
    "name": "chat",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "chat",
        "description": "chi-chat with AI"
    }
})

tool_manager.register_tool({
    "name":"comfort",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "comfort",
        "description": "comfort user to mitigate their bad emotion"
    }

})

tool_manager.register_tool({
    "name":"transfer",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "transfer",
        "description": "transfer the conversation to manual customer service"
    }
})

# retail tools
tool_manager.register_tool({
    "name":"daily_reception",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_daily_reception.daily_reception",
    "tool_def": {
        "name": "daily_reception",
        "description": "daily reception",
        "parameters":{
            "type":"object",
            "properties":{
                "response":{
                    "type": "string",
                    "description": "This tool handles daily responses from customer"
                }
            },
            "required": ["response"]
        },
       
    }
})


tool_manager.register_tool({
    "name":"goods_exchange",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_goods_exchage.goods_exchange",
    "tool_def": {
        "name": "goods_exchange",
        "description": "This tool handles user requests for product returns or exchanges."
    }
})

tool_manager.register_tool({
    "name":"customer_complain",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_customer_complain.customer_complain",
    "tool_def": {
        "name": "customer_complain",
        "description": "有关于客户抱怨的工具，比如商品质量，错发商品，漏发商品等",
    }
})

tool_manager.register_tool({
    "name":"promotion",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_promotion.promotion",
    "tool_def": {
        "name": "promotion",
        "description": "有关于商品促销的信息，比如返点，奖品和奖励等"
    }
})

tool_manager.register_tool({
    "name":"物流信息查询",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "物流信息查询",
        "description": "物流信息查询"
    }
})

tool_manager.register_tool({
    "name":"下单流程",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "下单流程",
        "description": "下单流程"
    }
})

tool_manager.register_tool({
    "name":"size_guide",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_size_guide.size_guide",
    "tool_def": {
        "name": "size_guide",
        "description": "size guide for customer, if the customer's weight unit is 斤, you should convert it to kg, 1斤=0.5kg",
        "parameters": {
            "type": "object",
            "properties": {
                "height": {
                    "description": "height of the customer",
                    "type": "int"
                },
                "weight": {
                    "description": "weight of the customer",
                    "type": "int"
                },
                "shoes_size": {
                    "description": "size of the customer's shoes",
                    "type": "float"
                },
                "foot_length": {
                    "description": "length of the customer's foot",
                    "type": "float"
                }
            },
            # "required": ["height", "weight", "shoes_size", "foot_length"]
            "required": []
        }
    }
})

# 商品信息查询
tool_manager.register_tool({
    "name":"goods_info",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_product_information_search.product_information_search",
    "tool_def": {
        "name": "goods_info",
        "description": "search the information of the product"
    }
})

# 商品推荐
tool_manager.register_tool({
    "name":"goods_recommendation",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_product_information_search.product_information_search",
    "tool_def": {
        "name": "goods_recommendation",
        "description": "recommend the product to the customer"
    }
})

# 下单流程
tool_manager.register_tool({
    "name":"order_pipeline",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_order_info.order_info",
    "tool_def": {
        "name": "order_pipeline",
        "description": "query the order information"
    }
})

# 物流信息查询
tool_manager.register_tool({
    "name":"delivery_track",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_order_info.order_info",
    "tool_def": {
        "name": "delivery_track",
        "description": "query the delivery information"
    }
})

tool_manager.register_tool({
    "name":"rule_response",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "rule_response",
        "description": "If a user's reply contains just a link or a long number, use this tool to reply."
    }
})

tool_manager.register_tool({
    "name":"下单流程",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "下单流程",
        "description": "下单流程"
    }
})

tool_manager.register_tool({
    "name":"促销查询",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "促销查询",
        "description": "促销查询"
    }
})

tool_manager.register_tool({
    "name":"转人工",
    "lambda_name": "xxxx",
    "lambda_module_path": "functions.retail_tools.lambda_human",
    "tool_def": {
        "name": "转人工",
        "description": "转人工"
    }
})
tool_manager.register_tool({
    "name":"信息缺失",
    "lambda_name": "xxxx",
    "lambda_module_path": "xxxx",
    "tool_def": {
        "name": "信息缺失",
        "description": "信息缺失"
    }
})

# 商品质量问题
tool_manager.register_tool(
    {
        "name":"product_quality",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.retail_tools.lambda_product_aftersales.product_aftersales",
        "tool_def": {
                "name": "product_quality",
                "description": "商品的售后处理，主要包括客户关于商品质量的抱怨等",
        }
    }
)

# 物流规则
tool_manager.register_tool(
    {
        "name":"product_logistics",
        "lambda_name": "xxxx",
        "lambda_module_path": "functions.retail_tools.lambda_product_aftersales.product_aftersales",
        "tool_def": {
                "name": "product_logistics",
                "description": "有关于商品物流的问题，主要运费包括退货，换货，错发商品，漏发商品等",
        }
    }
)
