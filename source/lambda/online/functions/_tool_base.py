from typing import Union,Callable
from langchain.pydantic_v1 import BaseModel,Field
from enum import Enum
from common_logic.common_utils.constant import SceneType,ToolRuningMode

class ToolDefType(Enum):
    openai = "openai"


class Tool(BaseModel):
    name: str = Field(description="tool name")
    lambda_name: str = Field(description="lambda name")
    lambda_module_path: Union[str, Callable] = Field(description="local module path")
    handler_name:str = Field(description="local handler name", default="lambda_handler")
    tool_def: dict = Field(description="tool definition")
    tool_init_kwargs:dict = Field(description="tool initial kwargs",default=None)
    running_mode: str = Field(description="tool running mode, can be loop or output", default=ToolRuningMode.LOOP)
    tool_def_type: ToolDefType = Field(description="tool definition type",default=ToolDefType.openai.value)
    scene: str = Field(description="tool use scene",default=SceneType.COMMON)
    # should_ask_parameter: bool = Field(description="tool use scene")

class ToolManager:
    def __init__(self) -> None:
        self.tools = {}
    
    def get_tool_id(self,tool_name:str,scene:str):
        return f"{tool_name}__{scene}"
    
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
        self.tools[self.get_tool_id(tool.name,tool.scene)] = tool

    def get_tool_by_name(self,name,scene=SceneType.COMMON):
        return self.tools[self.get_tool_id(name,scene)]
    
    # def get_names_from_tools_with_parameters(self):
    #     valid_tool_names_with_parameters = []
    #     for tool_name, tool_info in self.tools.items():
    #         if tool_info.running_mode == 'loop':
    #             valid_tool_names_with_parameters.append(tool_name)
    #     return valid_tool_names_with_parameters

tool_manager = ToolManager()
get_tool_by_name = tool_manager.get_tool_by_name



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
                    }},
                    "required": ["query"]
                },
            },
        "running_mode": "loop"
    }
)


##### default tools #########

tool_manager.register_tool({
    "name":"QA",
    "lambda_name": "",
    "lambda_module_path": "functions.lambda_retriever.retriever",
    "tool_def": {
                "name": "QA",
                "description": "answer question about aws according to searched relevant content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "description": "query to retrieve",
                            "type": "string"
                    }},
                    "required": ["query"]
                },
    },
    "running_mode": "loop"
})


# tool_manager.register_tool({
#     "name":"comfort",
#     "scenario":"common",
#     "lambda_name": "comfort",
#     "lambda_module_path": "functions.common_tools.comfort",
#     "tool_def": {
#         "name": "comfort",
#         "description": "comfort user to mitigate their bad emotion",
#         # "parameters": {
#         #     "type": "object",
#         #     "properties": {
#         #         "response": {
#         #             "description": "response to users",
#         #             "type": "string"
#         #     }},
#         #     "required": ["response"]
#         # },
#     },
#     "running_mode": "output"
# })

# tool_manager.register_tool({
#     "name":"transfer",
#     "lambda_name": "",
#     "lambda_module_path": "functions.common_tools.transfer",
#     "tool_def": {
#         "name": "transfer",
#         "description": "transfer the conversation to manual customer service",
#         # "parameters": {
#         #     "type": "object",
#         #     "properties": {
#         #         "response": {
#         #             "description": "response to users",
#         #             "type": "string"
#         #     }},
#         #     "required": ["response"]
#         # },
#     },
#     "running_mode": "output"
# })

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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
            Step1: Determin what type of goods the customer wants to buy according to the goods information in <商品信息> </商品信息> xml tag, such as shoes or apparel.
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
    },
    "running_mode": "output"
})

# 物流信息和规则查询
tool_manager.register_tool({
    "name":"product_logistics",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_order_info.order_info",
    "tool_def": {
        "name": "product_logistics",
        "description": "查询商品物流信息，运费规则和物流规则，其中运费规则包括退货，换货，错发商品，漏发商品等。物流规则包括发货时间等",
        # "parameters":{
        #     "required": ["response"]
        # },
    },
    "running_mode": "output",
    # "should_ask_parameter": "无需用户提供订单信息，物流单号",
})

# 商品库存信息
tool_manager.register_tool({
    "name":"goods_storage",
    "lambda_name": "",
    "lambda_module_path": "functions.retail_tools.lambda_order_info.order_info",
    "tool_def": {
        "name": "goods_storage",
        "description": "商品的库存信息，比如应对没货的情况等",
    },
    "running_mode": "output"
})


tool_manager.register_tool({
    "name":"rule_response",
    "lambda_name": "",
    "lambda_module_path": "",
    "tool_def": {
        "name": "rule_response",
        "description": "If a user's reply contains just a link or a long number, use this tool to reply.",
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
        # "parameters":{
        #     "required": ["response"]
        # },
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
