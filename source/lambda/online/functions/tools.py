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
    running_mode: str = Field(description="tool running mode, can be loop or output", default="loop")
    tool_def_type: ToolDefType = Field(description="tool definition type",default=ToolDefType.openai.value)
    should_ask_parameter: str = Field(description="whether should ask about parameters of tools", default="True")
    

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
    
    def get_names_from_tools_with_parameters(self):
        valid_tool_names_with_parameters = []
        for tool_name, tool_info in self.tools.items():
            if tool_info.running_mode == 'loop':
                valid_tool_names_with_parameters.append(tool_name)
        return valid_tool_names_with_parameters

tool_manager = ToolManager()
get_tool_by_name = tool_manager.get_tool_by_name

tool_manager.register_tool({
    "name": "get_weather",
    "lambda_name": "",
    "lambda_module_path": "functions.lambda_get_weather.get_weather",
    "tool_def":{
            "name": "get_weather",
            "description": "Get the current weather for `city_name`",
            "parameters": {
                "type": "object",
                "properties": {
                "city_name": {
                    "description": "The name of the city to be queried",
                    "type": "string"
                }, 
                },
                "required": ["city_name"]
            }
        },
    "running_mode": "loop"
    }
)


tool_manager.register_tool(
    {
        "name":"give_rhetorical_question",
        "lambda_name": "",
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
        },
        "running_mode": "output"
    }
)



tool_manager.register_tool(
    {
        "name": "give_final_response",
        "lambda_name": "",
        "lambda_module_path": "",
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
        },
        "running_mode": "output"
    }
)


tool_manager.register_tool(
    {
        "name":"search_lihoyo",
        "lambda_name": "",
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
        },
        "running_mode": "loop"
    }
)



##### default tools #########
tool_manager.register_tool({
    "name": "service_availability",
    "lambda_name": "check_service_availability",
    "lambda_module_path": "functions.lambda_aws_api.check_service_availability",
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
        "running_mode": "loop"
    }
})


tool_manager.register_tool({
    "name": "explain_abbr",
    "lambda_name": "",
    "lambda_module_path": "",
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
        "running_mode": "output"
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
        },
        "running_mode": "loop"
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
        },
        "running_mode": "loop"
    }
})

tool_manager.register_tool({
    "name":"assist",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "assist",
        "description": "assist user to do some office work",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"QA",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "QA",
        "description": "answer question about aws according to searched relevant content",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name": "chat",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "chat",
        "description": "chi-chat with AI",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"comfort",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "comfort",
        "description": "comfort user to mitigate their bad emotion",
    },
    "running_mode": "output"

})

tool_manager.register_tool({
    "name":"transfer",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "transfer",
        "description": "transfer the conversation to manual customer service",
    },
    "running_mode": "output"
})

# retail tools
tool_manager.register_tool({
    "name":"daily_reception",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_daily_reception.daily_reception",
    "tool_def": {
        "name": "daily_reception",
        "description": "daily reception",
        "parameters":{
            # "type":"object",
            # "properties":{
            #     "response":{
            #         "type": "string",
            #         "description": "This tool handles daily responses from customer"
            #     }
            # },
            # "required": ["response"]
        },
    },
    "running_mode": "output"
})


tool_manager.register_tool({
    "name":"goods_exchange",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_goods_exchage.goods_exchange",
    "tool_def": {
        "name": "goods_exchange",
        "description": "This tool handles user requests for product returns or exchanges.",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"customer_complain",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_customer_complain.customer_complain",
    "tool_def": {
        "name": "customer_complain",
        "description": "有关于客户抱怨的工具，比如商品质量，错发商品，漏发商品等",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"promotion",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_promotion.promotion",
    "tool_def": {
        "name": "promotion",
        "description": "有关于商品促销的信息，比如返点，奖品和奖励等",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"物流信息查询",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "物流信息查询",
        "description": "物流信息查询",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"下单流程",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "下单流程",
        "description": "下单流程",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"size_guide",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_size_guide.size_guide",
    "tool_def": {
        "name": "size_guide",
        "description": """size guide for customer
            Step1: Determin what type of goods the customer wants to buy according to the goods information in <goods_info></goods_info> xml tag, such as shoes or apparel.
            Step2: If the customer wants to buy shoes, you should provide the customer's shoes_size or foot_length.
            Step3: If the customer wants to buy apparel, you should provide the customer's height and weight.
            Notice: if the customer's weight unit is 斤, you should convert it to kg, 1斤=0.5kg""",
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
        },
    },
    "running_mode": "loop"
})

# 商品信息查询
tool_manager.register_tool({
    "name":"goods_info",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_product_information_search.product_information_search",
    "tool_def": {
        "name": "goods_info",
        "description": "search the information of the product, do not ask the user for more information",
    },
    "running_mode": "output"
})

# 商品推荐
tool_manager.register_tool({
    "name":"goods_recommendation",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_product_information_search.product_information_search",
    "tool_def": {
        "name": "goods_recommendation",
        "description": "recommend the product to the customer",
    },
    "running_mode": "output"
})

# 下单流程
tool_manager.register_tool({
    "name":"order_pipeline",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_order_info.order_info",
    "tool_def": {
        "name": "order_pipeline",
        "description": "query the order information",
    },
    "running_mode": "output"
})

# 物流信息查询
tool_manager.register_tool({
    "name":"delivery_track",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_order_info.order_info",
    "tool_def": {
        "name": "delivery_track",
        "description": "查询物流信息，还包括有关于商品物流的问题，主要运费包括退货，换货，错发商品，漏发商品等。 也包括什么时候发货，发货地址等信息。",
    },
    "running_mode": "output",
    # "should_ask_parameter": "无需用户提供订单信息，物流单号",
})

tool_manager.register_tool({
    "name":"rule_response",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "rule_response",
        "description": "If a user's reply contains just a link or a long number, use this tool to reply.",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"下单流程",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "下单流程",
        "description": "下单流程",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"促销查询",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "促销查询",
        "description": "促销查询",
    },
    "running_mode": "output"
})

tool_manager.register_tool({
    "name":"转人工",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_human",
    "tool_def": {
        "name": "转人工",
        "description": "转人工",
    },
    "running_mode": "output"
})
tool_manager.register_tool({
    "name":"信息缺失",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "信息缺失",
        "description": "信息缺失",
    },
    "running_mode": "output"
})

# 商品质量问题
tool_manager.register_tool(
    {
        "name":"product_quality",
        "lambda_name": "",
        "lambda_module_path": "functions.retail_tools.lambda_product_aftersales.product_aftersales",
        "tool_def": {
            "name": "product_quality",
            "description": "商品的售后处理，主要包括客户关于商品质量的抱怨，比如开胶等问题的",
            "parameters": {
                "type": "object",
                "properties": {
                    "shop": {
                        "description": """The shop which the customer bought the product.
                         If the customer do not provide the shop name, the shop name is 'tianmao' by default.
                         The shop name must be in the list of ['tianmao', 'taobao','jingdong','dewu','other']""",
                        "type": "str"
                    }
                },
                "required": []
            }
        },
        "running_mode": "output"
    }
)

# 物流规则
tool_manager.register_tool(
    {
        "name":"product_logistics",
        "lambda_name": "",
        "lambda_module_path": "functions.retail_tools.lambda_product_aftersales.product_aftersales",
        "tool_def": {
                "name": "product_logistics",
                "description": "有关于商品物流的问题，主要运费包括退货，换货，错发商品，漏发商品等。也包括什么时候发货，发货地址，货仓等信息。",
        },
        "running_mode": "output",
        # "should_ask_parameter": "无需用户提供订单信息，物流单号",
    }
)
