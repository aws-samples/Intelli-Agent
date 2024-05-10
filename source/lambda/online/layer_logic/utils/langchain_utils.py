import threading
import time
from functools import partial
from typing import TypedDict,Annotated

from langchain.schema.runnable import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain.schema.runnable.base import Runnable, RunnableLambda
from prettytable import PrettyTable

# import threading
# import time
from .logger_utils import logger
from .python_utils import update_nest_dict


class RunnableDictAssign:
    """
    example:
      def fn(x):
          return {"a":1,"b":2}

       chain = RunnableDictAssign(fn)
       chain.invoke({"c":3})

       ## output
       {"c":3,"a":1,"b":2}
    """

    def __new__(cls, fn):
        assert callable(fn)

        def _merge_keys(x: dict, key="__temp_dict"):
            d = x.pop(key)
            return {**x, **d}

        chain = RunnablePassthrough.assign(__temp_dict=fn) | RunnableLambda(
            lambda x: _merge_keys(x)
        )
        return chain


class RunnableParallelAssign:
    """
    example:
      def fn(x):
          return {"a":1,"b":2}

       chain = RunnableDictAssign(fn)
       chain.invoke({"c":3})

       ## output
       {"c":3,"a":1,"b":2}
    """

    def __new__(cls, **kwargs):
        def _merge_keys(x: dict, key="__temp_dict"):
            d = x.pop(key)
            return {**x, **d}

        chain = RunnablePassthrough.assign(
            __temp_dict=RunnableParallel(**kwargs)
        ) | RunnableLambda(lambda x: _merge_keys(x))
        return chain


class RunnableNoneAssign:
    """
    example:
      def fn(x):
          return None

       chain = RunnableNoneAssign(fn)
       chain.invoke({"c":3})

       ## output
       {"c":3}
    """

    def __new__(cls, fn):
        assert callable(fn)

        def _remove_keys(x: dict, key="__temp_dict"):
            x.pop(key)
            return x

        chain = RunnablePassthrough.assign(__temp_dict=fn) | RunnableLambda(
            lambda x: _remove_keys(x)
        )
        return chain


def create_identity_lambda(keys: list):
    if isinstance(keys, str):
        keys = [keys]
    assert isinstance(keys, list) and keys, keys

    assert isinstance(keys[0], str), keys

    ret = {k: lambda x: x[k] for k in keys}
    return ret


def _add_key_to_debug(x, add_key, debug_key="debug_info"):
    x[debug_key][add_key] = x[add_key]
    return x


def add_key_to_debug(add_key, debug_key="debug_info"):
    return RunnableLambda(
        partial(_add_key_to_debug, add_key=add_key, debug_key=debug_key)
    )


class LogTimeListener:
    trace_infos_lock = threading.Lock()

    def __init__(
        self,
        chain_name,
        message_id="",
        log_input=False,
        log_output=False,
        log_input_template=None,
        log_output_template=None,
        trace_infos=None,
    ):
        self.chain_name = chain_name
        self.message_id = message_id
        self.log_input = log_input
        self.log_output = log_output
        self.log_input_template = log_input_template
        self.log_output_template = log_output_template
        self.message_id = message_id
        self.start_time = None
        self.trace_infos = trace_infos

    def on_start(self, run):
        logger.info(f"{self.message_id} Enter: {self.chain_name}")
        if self.log_input:
            logger.info(f"Inputs({self.chain_name}): {run.inputs}")
        if self.log_input_template:
            logger.info(self.log_input_template.format(**run.inputs))

        if self.trace_infos is not None:
            with self.trace_infos_lock:
                self.trace_infos.append(
                    {
                        "chain_name": self.chain_name,
                        "action": "enter",
                        "create_time": time.time(),
                    }
                )

    def on_end(self, run):
        if self.log_output:
            logger.info(f"Outputs({self.chain_name}): {run.outputs}")

        if self.log_output_template:
            if isinstance(run.outputs, dict):
                logger.info(self.log_output_template.format(**run.outputs))
            else:
                logger.info(self.log_output_template.format(run.outputs))
        exe_time = (run.end_time - run.start_time).total_seconds()
        logger.info(
            f"{self.message_id} Exit: {self.chain_name}, elpase time(s): {exe_time}"
        )
        logger.info(f"{self.message_id} running time of {self.chain_name}: {exe_time}s")

        if self.trace_infos is not None:
            with self.trace_infos_lock:
                self.trace_infos.append(
                    {
                        "chain_name": self.chain_name,
                        "action": "exit",
                        "create_time": time.time(),
                    }
                )

    def on_error(self, run):
        raise
        # logger.info(f"Error in run chain: {self.chain_name}.")


def chain_logger(
    chain,
    chain_name,
    message_id=None,
    log_input=False,
    log_output=False,
    log_input_template=None,
    log_output_template=None,
    trace_infos=None,
):
    obj = LogTimeListener(
        chain_name,
        message_id,
        log_input=log_input,
        log_output=log_output,
        log_input_template=log_input_template,
        log_output_template=log_output_template,
        trace_infos=trace_infos,
    )
    new_chain = chain.with_listeners(
        on_start=obj.on_start, on_end=obj.on_end, on_error=obj.on_error
    )
    return new_chain


def format_trace_infos(trace_infos: list, use_pretty_table=True):
    trace_infos = sorted(trace_infos, key=lambda x: x["create_time"])
    trace_info_strs = []

    if use_pretty_table:
        table = PrettyTable()
        table.field_names = ["chain_name", "create_time", "action"]
        table.add_rows(
            [
                (
                    trace_info["chain_name"],
                    trace_info["create_time"],
                    trace_info["action"],
                )
                for trace_info in trace_infos
            ]
        )
        return str(table)

    for trace_info in trace_infos:
        trace_info_strs.append(
            f"time: {trace_info['create_time']}, action: {trace_info['action']}, chain: {trace_info['chain_name']}, "
        )

    return "\n".join(trace_info_strs)


class NestUpdateState(TypedDict):
    keys: Annotated[dict,update_nest_dict]