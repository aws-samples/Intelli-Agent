class LambdaInvokeError(Exception):
    pass


class ToolNotExistError(Exception):
    def __init__(self, tool_name,function_call_content) -> None:
        self.tool_name = tool_name
        self.function_call_content = function_call_content
    
    def to_agent(self):
        return f"tool: {self.tool_name} is currently unavailable."

    def __str__(self):
        return self.to_agent() + "\nfunction_call:\n{self.function_call_content}"
    
    
class ToolParameterNotExistError(Exception):
    def __init__(self, tool_name,parameter_key,function_call_content) -> None:
        self.tool_name = tool_name
        self.parameter_key = parameter_key
        self.function_call_content = function_call_content

    def to_agent(self):
        return f"The parameter ”{self.parameter_key}“ is required when calling tool: {self.tool_name}."

    def __str__(self):
        return self.to_agent() + f"\nfunction_call:\n{self.function_call_content}"


class MultipleToolNameError(Exception):
    def __init__(self,function_call_content) -> None:
        self.function_call_content = function_call_content

    def to_agent(self):
        return "multiple tool names are found in XML tag <invoke></invoke>."

    def __str__(self):
        return self.to_agent() + f"\nfunction_call:\n{self.function_call_content}"
