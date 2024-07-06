from common_logic.common_utils.constant import EntryType
from .._tool_base import tool_manager 


SCENE = EntryType.COMMON  

tool_manager.register_tool({
    "name": "get_weather",
    "scene": SCENE,
    "lambda_module_path": "functions.common_tools.get_weather",
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






