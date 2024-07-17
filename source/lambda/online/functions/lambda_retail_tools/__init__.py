from common_logic.common_utils.constant import SceneType,ToolRuningMode
from .._tool_base import tool_manager 
from . import daily_reception
from . import goods_exchange
from . import customer_complain
from .  import size_guide
from . import product_information_search
from . import order_info
from . import product_aftersales
from ..lambda_common_tools import give_rhetorical_question  
from ..lambda_common_tools import give_final_response
from . import rule_response
from . import transfer
from . import promotion


SCENE = SceneType.RETAIL  
LAMBDA_NAME = "lambda_retail_tools"


tool_manager.register_tool({
    "name":"daily_reception",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": daily_reception.lambda_handler,
    "tool_def": {
        "name": "daily_reception",
        "description": "daily reception",
        "parameters":{
        },
    },
    "running_mode": ToolRuningMode.ONCE
})


tool_manager.register_tool({
    "name":"goods_exchange",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": goods_exchange.lambda_handler,
    "tool_def": {
        "name": "goods_exchange",
        "description": "This tool handles user requests for product returns or exchanges.",
    },
    "running_mode": ToolRuningMode.ONCE
})


tool_manager.register_tool({
    "name": "customer_complain",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": customer_complain.lambda_handler,
    "tool_def": {
        "name": "customer_complain",
        "description": "有关于客户抱怨的工具，比如商品质量，错发商品，漏发商品等",
    },
    "running_mode": ToolRuningMode.ONCE
})


tool_manager.register_tool({
    "name":"promotion",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": promotion.lambda_handler,
    "tool_def": {
        "name": "promotion",
        "description": "有关于商品促销的信息，比如返点，奖品和奖励等",
    },
    "running_mode": ToolRuningMode.ONCE
})


tool_manager.register_tool({
    "name":"size_guide",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": size_guide.lambda_handler,
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
    "running_mode": ToolRuningMode.LOOP
})


tool_manager.register_tool({
    "name":"goods_recommendation",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": product_information_search.lambda_handler,
    "tool_def": {
        "name": "goods_recommendation",
        "description": "recommend the product to the customer",
    },
    "running_mode": ToolRuningMode.ONCE
})


tool_manager.register_tool({
    "name":"order_pipeline",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": order_info.lambda_handler,
    "tool_def": {
        "name": "order_pipeline",
        "description": "query the order information",
    },
    "running_mode": ToolRuningMode.ONCE
})


tool_manager.register_tool({
    "name":"product_logistics",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": order_info.lambda_handler,
    "tool_def": {
        "name": "product_logistics",
        "description": "查询商品物流信息，运费规则和物流规则，其中运费规则包括退货，换货，错发商品，漏发商品等。物流规则包括发货时间等",
    },
    "running_mode": ToolRuningMode.ONCE,
})


tool_manager.register_tool({
    "name":"goods_storage",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": order_info.lambda_handler,
    "tool_def": {
        "name": "goods_storage",
        "description": "商品的库存信息，比如应对没货的情况等",
    },
    "running_mode": ToolRuningMode.ONCE,
})


tool_manager.register_tool({
    "name": "rule_response",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": rule_response.lambda_handler,
    "tool_def": {
        "name": "rule_response",
        "description": "If a user's reply contains just a link or a long number, use this tool to reply.",
    },
    "running_mode": ToolRuningMode.ONCE,
})


tool_manager.register_tool({
    "name":"transfer",
    "scene": SCENE,
    "lambda_name": LAMBDA_NAME,
    "lambda_module_path": transfer.lambda_handler,
    "tool_def": {
        "name": "转人工",
        "description": "转人工"
    },
    "running_mode": ToolRuningMode.ONCE
})


tool_manager.register_tool(
    {
        "name":"product_quality",
        "scene": SCENE,
        "lambda_name": LAMBDA_NAME,
        "lambda_module_path": product_aftersales.lambda_handler,
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
        "running_mode": ToolRuningMode.ONCE
    }
)


tool_manager.register_tool(
    {
        "name":"give_rhetorical_question",
        "scene": SCENE,
        "lambda_name": LAMBDA_NAME,
        "lambda_module_path": give_rhetorical_question.lambda_handler,
        "tool_def":{
                "name": "give_rhetorical_question",
                "description": "If the user's question is not clear and specific, resulting in the inability to call other tools, please call this tool to ask the user a rhetorical question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "description": "The rhetorical question to user",
                            "type": "string"
                    },
                    },
                    "required": ["question"],
                },
            },
        "running_mode": ToolRuningMode.ONCE
    }
)


tool_manager.register_tool(
    {
        "name": "give_final_response",
        "scene": SCENE,
        "lambda_name": LAMBDA_NAME,
        "lambda_module_path": give_final_response.lambda_handler,
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
                },
            },
         "running_mode": ToolRuningMode.ONCE
    }
)











