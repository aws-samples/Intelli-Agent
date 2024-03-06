from langchain.schema.runnable.base import Runnable,RunnableLambda
from langchain.schema.runnable import RunnablePassthrough
from functools import partial
from langchain.schema.callbacks.base import BaseCallbackHandler
# import threading
# import time 
from .logger_utils import logger
from langchain.schema.runnable import RunnableLambda,RunnablePassthrough,RunnableParallel

# class LmabdaDict(dict):
#     """add lambda to value"""
#     def __init__(self,**kwargs):
#         super().__init__(**kwargs)
#         for k in list(self.keys()):
#             v = self[k]
#             if not callable(v) or not isinstance(v,Runnable):
#                 self[k] = lambda x:x

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
    def __new__(cls,fn):
        assert callable(fn)
        def _merge_keys(x:dict,key='__temp_dict'):
            d = x.pop(key)
            return {**x,**d}
        chain = RunnablePassthrough.assign(__temp_dict=fn) | RunnableLambda(lambda x: _merge_keys(x))
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
    def __new__(cls,**kwargs):
        def _merge_keys(x:dict,key='__temp_dict'):
            d = x.pop(key)
            return {**x,**d}
        chain = RunnablePassthrough.assign(__temp_dict=RunnableParallel(**kwargs)) | RunnableLambda(lambda x: _merge_keys(x))
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
    def __new__(cls,fn):
        assert callable(fn)
        def _remove_keys(x:dict,key='__temp_dict'):
            x.pop(key)
            return x
        chain = RunnablePassthrough.assign(__temp_dict=fn) | RunnableLambda(lambda x: _remove_keys(x))
        return chain




def create_identity_lambda(keys:list):
    if isinstance(keys,str):
        keys = [keys]
    assert isinstance(keys,list) and keys, keys
     
    assert isinstance(keys[0],str), keys
    
    ret = {k:lambda x:x[k] for k in keys}
    return ret

def _add_key_to_debug(x,add_key,debug_key="debug_info"):
    x[debug_key][add_key] = x[add_key]
    return x

def add_key_to_debug(add_key,debug_key="debug_info"):
    return RunnableLambda(partial(_add_key_to_debug,add_key=add_key,debug_key=debug_key))


class LogTimeListener:
    def __init__(
            self,
            chain_name,
            message_id,
            log_input=False,
            log_output=False,
            log_input_template=None,
            log_output_template=None
        ):
        self.chain_name = chain_name
        self.log_input = log_input
        self.log_output = log_output
        self.log_input_template = log_input_template
        self.log_output_template = log_output_template

    def on_start(self,run):
        logger.info(f'{self.message_id} Enter: {self.chain_name}')
        if self.log_input:
            logger.info(f"Inputs({self.chain_name}): {run.inputs}")
        if self.log_input_template:
            logger.info(self.log_input_template.format(**run.inputs))
    def on_end(self,run):
        if self.log_output:
            logger.info(f'Outputs({self.chain_name}): {run.outputs}')
        
        if self.log_output_template:
            logger.info(self.log_output_template.format(**run.outputs))
            
        exe_time = (run.end_time - run.start_time).total_seconds()
        logger.info(f'{self.message_id} Exit: {self.chain_name}, elpase time(s): {exe_time}')
        logger.info(f'{self.message_id} running time of {self.chain_name}: {exe_time}s')
        
    def on_error(self,run):
        raise 
        # logger.info(f"Error in run chain: {self.chain_name}.")

def chain_logger(
        chain,
        chain_name,
        message_id=None,
        log_input=False,
        log_output=False,
        log_input_template=None,
        log_output_template=None
        ):
    obj = LogTimeListener(
        chain_name,
        message_id,
        log_input=log_input,
        log_output=log_output,log_input_template=log_input_template,
        log_output_template=log_output_template
        ) 
    new_chain = chain.with_listeners(on_start=obj.on_start, on_end=obj.on_end, on_error=obj.on_error)
    return new_chain