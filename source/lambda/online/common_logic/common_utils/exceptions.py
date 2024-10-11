class LambdaInvokeError(Exception):
    pass


class ToolExceptionBase(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.agent_message = None
        self.error_message = None

    def to_agent(self):
        raise NotImplementedError


class ToolNotExistError(ToolExceptionBase):
    def __init__(self, tool_name, function_call_content) -> None:
        super().__init__()
        self.tool_name = tool_name
        self.function_call_content = function_call_content

    def to_agent(self):
        return f"tool: {self.tool_name} is currently unavailable."

    def __str__(self):
        return self.to_agent() + f"\nfunction_call:\n{self.function_call_content}"


class ToolParameterNotExistError(ToolExceptionBase):
    def __init__(self, tool_name, parameter_key, function_call_content, tool_format=None) -> None:
        super().__init__()
        self.tool_name = tool_name
        self.parameter_key = parameter_key
        self.function_call_content = function_call_content
        self.tool_format = tool_format

    def to_agent(self):
        value = f"The parameter ”{self.parameter_key}“ is required when calling tool: {self.tool_name}."
        if self.tool_format:
            value += self.tool_format
        return value

    def __str__(self):
        return self.to_agent() + f"\nfunction_call:\n{self.function_call_content}"


class MultipleToolNameError(ToolExceptionBase):
    def __init__(self, function_call_content) -> None:
        super().__init__()
        self.function_call_content = function_call_content
        self.tool_name = ""

    def to_agent(self):
        return "multiple tool names are found in XML tag <invoke></invoke>."

    def __str__(self):
        return self.to_agent() + f"\nfunction_call:\n{self.function_call_content}"


class ToolNotFound(ToolExceptionBase):
    def __str__(self):
        return "no tool found"
