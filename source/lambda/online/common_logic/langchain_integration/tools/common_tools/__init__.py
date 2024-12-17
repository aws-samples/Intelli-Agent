from typing import Optional, Dict, Any
import sys
from io import StringIO

from .. import lazy_tool_load_decorator, ToolIdentifier, ToolManager
from common_logic.common_utils.constant import SceneType


@lazy_tool_load_decorator(SceneType.COMMON, "get_weather")
def _load_weather_tool(tool_identifier: ToolIdentifier):
    from . import get_weather
    tool_def = {
        "description": "Get the current weather for `city_name`",
        "properties": {
            "city_name": {
                "description": "The name of the city. If the city name does not appear visibly in the user's response, please call the `give_rhetorical_question` to ask for city name.",
                "type": "string"
            },
        },
        "required": ["city_name"]
    }
    ToolManager.register_func_as_tool(
        func=get_weather.get_weather,
        tool_def=tool_def,
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        return_direct=False
    )


@lazy_tool_load_decorator(SceneType.COMMON, "give_rhetorical_question")
def _load_rhetorical_tool(tool_identifier: ToolIdentifier):
    from . import give_rhetorical_question
    tool_def = {
        "description": "This tool is designed to handle the scenario when required parameters are missing from other tools. It prompts the user to provide the necessary information, ensuring that all essential parameters are collected before proceeding. This tools enhances user interaction by clarifying what is needed and improving the overall usability of the application.",
        "properties": {
            "question": {
                "description": "The rhetorical question to user. Example:\nInput: 今天天气怎么样?\nOutput: 请问您想了解哪个城市的天气?",
                "type": "string"
            },
        },
        "required": ["question"]
    }
    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=give_rhetorical_question.give_rhetorical_question,
        tool_def=tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON, "give_final_response")
def _load_final_response_tool(tool_identifier: ToolIdentifier):
    from . import give_final_response

    tool_def = {
        "description": "If none of the other tools need to be called, call the current tool to complete the direct response to the user.",
        "properties": {
            "response": {
                "description": "Response to user",
                "type": "string"
            }
        },
        "required": ["response"]
    }
    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=give_final_response.give_final_response,
        tool_def=tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON, "chat")
def _load_chat_tool(tool_identifier: ToolIdentifier):
    from . import chat
    tool_def = {
        "description": "casual talk with AI",
        "properties": {
            "response": {
                "description": "response to users",
                "type": "string"
            }
        },
        "required": ["response"]
    }

    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=chat.chat,
        tool_def=tool_def,
        return_direct=True
    )


@lazy_tool_load_decorator(SceneType.COMMON, "rag_tool")
def _load_rag_tool(tool_identifier: ToolIdentifier):
    from . import rag
    tool_def = {
        "description": "private knowledge",
        "properties": {
            "query": {
                "description": "query for retrieve",
                "type": "string"
            }
        }
    }
    ToolManager.register_func_as_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        func=rag.rag_tool,
        tool_def=tool_def,
        return_direct=True
    )


################### langchain tools #######################

@lazy_tool_load_decorator(SceneType.COMMON, "python_repl")
def _loadd_python_repl_tool(tool_identifier: ToolIdentifier):
    from langchain_core.tools import Tool
    from langchain_experimental.utilities import PythonREPL as _PythonREPL
    from langchain_experimental.utilities.python import warn_once
    import multiprocessing

    # modify LangChain's PythonREPL to adapt aws lambda,
    # where it's execution environment not having /dev/shm

    class PythonREPL(_PythonREPL):
        @classmethod
        def worker(
            cls,
            command: str,
            globals: Optional[Dict],
            locals: Optional[Dict],
            conn: Any,
        ) -> None:
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            try:
                cleaned_command = cls.sanitize_input(command)
                exec(cleaned_command, globals, locals)
                sys.stdout = old_stdout
                conn.send(mystdout.getvalue())
            except Exception as e:
                sys.stdout = old_stdout
                conn.send(repr(e))
            conn.close()

        def run(self, command: str, timeout: Optional[int] = None) -> str:
            """Run command with own globals/locals and returns anything printed.
            Timeout after the specified number of seconds."""

            # Warn against dangers of PythonREPL
            warn_once()

            # queue: multiprocessing.Queue = multiprocessing.Queue()
            parent_conn, child_conn = multiprocessing.Pipe()

            # Only use multiprocessing if we are enforcing a timeout
            if timeout is not None:
                # create a Process
                p = multiprocessing.Process(
                    target=self.worker, args=(
                        command, self.globals, self.locals, child_conn)
                )

                # start it
                p.start()

                # wait for the process to finish or kill it after timeout seconds
                p.join(timeout)

                if p.is_alive():
                    p.terminate()
                    return "Execution timed out"
            else:
                self.worker(command, self.globals, self.locals, child_conn)
            # get the result from the worker function
            return parent_conn.recv()

    python_repl = PythonREPL()

    def _run(command: str, timeout=None) -> str:
        res = python_repl.run(command=command, timeout=timeout)
        if not res:
            raise ValueError(
                f"The current tool does not produce a result, modify your code and continue to call the `python_repl` tool, making sure to use the `print` function to output the final result.")
        return res

    description = """\
This tool handles scientific computing problems by executing python code. Typical scenarios include the follows:
1. Mathematical arithmetic/numerical comparisons.
2. Code execution scenarios, such as data analysis, visualization, etc.

Input should be a valid python code. If you want to see the output of a value, you must print it out with `print(...)` statement.
"""
    repl_tool = Tool(
        name="python_repl",
        description=description,
        func=_run
    )
    ToolManager.register_lc_tool(
        scene=tool_identifier.scene,
        name=tool_identifier.name,
        tool=repl_tool
    )
