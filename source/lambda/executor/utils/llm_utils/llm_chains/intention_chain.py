from .llm_chain_base import LLMChain
from ...constant import INTENT_RECOGNITION_TYPE,IntentType
from ..llm_models import Model
import json 
import os
import sys
from random import Random
from functools import lru_cache
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableBranch, RunnableLambda
from .chat_chain import Iternlm2Chat7BChatChain
from ...prompt_template import INTENT_RECOGINITION_EXAMPLE_TEMPLATE, \
    INTENT_RECOGINITION_PROMPT_TEMPLATE_CLUADE

abs_dir = os.path.dirname(__file__)

intent_save_path = os.path.join(
    os.path.dirname(os.path.dirname(abs_dir)),
    'intent_utils',
    "intent_examples",
    "examples.json"
)

@lru_cache()
def load_intention_file(
    intent_save_path=intent_save_path,
    seed=42
    ):
    intent_few_shot_examples = json.load(open(intent_save_path))
    intent_indexs = {intent_d['intent']:intent_d['index'] for intent_d in intent_few_shot_examples['intents']}
    few_shot_examples = []
    intents = list(intent_few_shot_examples['examples'].keys())
    for intent in intents:
        examples = intent_few_shot_examples['examples'][intent]
        for query in examples:
            few_shot_examples.append({
                "intent":intent,
                "query": query
            })
    # shuffle
    Random(seed).shuffle(few_shot_examples)
    return {
        "few_shot_examples": few_shot_examples,
        "intent_indexs":intent_indexs,
    }


class Iternlm2Chat7BIntentRecognitionChain(Iternlm2Chat7BChatChain):
    model_id = "internlm2-chat-7b"
    intent_type = INTENT_RECOGNITION_TYPE

    default_model_kwargs = {
        "temperature":0.1,
        "max_new_tokens": 100,
        "stop_tokens": ["\n",'。','.']
    }

    @classmethod
    def create_prompt(cls,x):
        r = load_intention_file(intent_save_path)
        few_shot_examples = r['few_shot_examples']
        # intent_indexs = r['intent_indexs']
        exmaple_template = "问题: {query}\n类别: {label}"
        example_strs = []
        for example in few_shot_examples:
            example_strs.append(exmaple_template.format(query=example['query'],label=example['intent']))

        example_str = "\n\n".join(example_strs)

        meta_instruction = f'你是一个问题分类助理，正在对用户的问题进行分类。为了辅助你进行问题分类，下面给出一些示例:\n{example_str}'
        query_str = exmaple_template.format(query=x['query'],label="")
        prompt_template = """请对下面的问题进行分类:
        {query_str}
        """
        prompt = cls.build_prompt(
            prompt_template.format(query_str=query_str),
            meta_instruction=meta_instruction
        )
        prompt = prompt + f"根据前面给到的示例, 问题{x['query']}属于类别:"

        return prompt
    
    @staticmethod
    def postprocess(intent):
        intent = intent.replace('。',"").replace('.',"").strip().strip('**')
        r = load_intention_file(intent_save_path)
        intent_indexs = r['intent_indexs']
        assert intent in intent_indexs, (intent,intent_indexs)
        return intent

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}
        chain = super().create_chain(
            model_kwargs=model_kwargs,
            **kwargs
        )
        chain = chain | RunnableLambda(lambda x:cls.postprocess(x))
        return chain

class Iternlm2Chat20BIntentRecognitionChain(Iternlm2Chat7BIntentRecognitionChain):
    model_id = "internlm2-chat-20b"

class Claude2IntentRecognitionChain(LLMChain):
    model_id = 'anthropic.claude-v2'
    intent_type = INTENT_RECOGNITION_TYPE

    default_model_kwargs = {
      "temperature": 0,
      "max_tokens_to_sample": 2000,
      "stop_sequences": [
        "\n\n",
        "\n\nHuman:"
      ]
    }

    @classmethod
    def create_few_shot_examples(cls):
        ret = []
        for intent in cls.intents:
            examples = cls.intent_few_shot_examples['examples'][intent]
            for query in examples:
                ret.append({
                    "intent":intent,
                    "query": query
                })
        return ret
    

    @classmethod
    def create_few_shot_example_string(cls,example_template=INTENT_RECOGINITION_EXAMPLE_TEMPLATE):
        example_strs = []
        intent_indexs = cls.intent_indexs
        for example in cls.few_shot_examples:
            example_strs.append(
                example_template.format(
                    label=intent_indexs[example['intent']],
                    query=example['query']
                    )
            )
        return '\n\n'.join(example_strs)

    @classmethod
    def create_all_labels_string(cls):
        intent_few_shot_examples = cls.intent_few_shot_examples
        label_strs = []
        labels = intent_few_shot_examples['intents']
        for i,label in enumerate(labels):
            label_strs.append(f"({label['index']}) {label['describe']}")
        return "\n".join(label_strs)

    def postprocess(self,output:str):
        out = output.strip()
        assert out, output
        return self.index_intents[out[0]]

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        r = load_intention_file(intent_save_path)
        cls.few_shot_examples = r['few_shot_examples']
        cls.intent_indexs = r['intent_indexs']

        cls.index_intents = {v:k for k,v in  cls.intent_indexs.items()}
        cls.intents = list(cls.intent_few_shot_examples['examples'].keys())
        cls.few_shot_examples = cls.create_few_shot_examples()

        cls.examples_str = cls.create_few_shot_example_string(example_template=INTENT_RECOGINITION_EXAMPLE_TEMPLATE)
        cls.categories_str = cls.create_all_labels_string()

        intent_recognition_template = PromptTemplate.from_template(INTENT_RECOGINITION_PROMPT_TEMPLATE_CLUADE)
        

        model_kwargs = model_kwargs or {}
        model_kwargs = {**cls.default_model_kwargs,**model_kwargs}

        llm = Model.get_model(cls.model_id,model_kwargs=model_kwargs)

        chain = intent_recognition_template | RunnableLambda(lambda x:llm.invoke(
            {"categories":cls.categories_str,
             "examples":cls.examples_str,
             'query':x['query']})) | RunnableLambda(lambda x:x.dict()['content']) | RunnableLambda(lambda x: cls.postprocess(x))
     
        return chain 
        
        
class Claude21IntentRecognitionChain(Claude2IntentRecognitionChain):
    model_id = 'anthropic.claude-v2:1'


class ClaudeInstanceIntentRecognitionChain(Claude2IntentRecognitionChain):
    model_id = 'anthropic.claude-instant-v1'








    
        
        




        




