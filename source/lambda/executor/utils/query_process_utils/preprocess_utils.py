import re
import boto3
from ..service_intent_recognition.utils import get_service_name
from ..llm_utils.llm_models import Model
from ..llm_utils.llm_chains import LLMChain
from ..constant import QUERY_TRANSLATE_TYPE,AWS_TRANSLATE_SERVICE_MODEL_ID,\
QUERY_TRANSLATE_IDENTITY_TYPE

from .bert_tokenization import BasicTokenizer
# language symbols
CHINESE = 'zh'
ENGLISH = 'en'

language_text_map = {}
language_text_map[CHINESE] = "中文"
language_text_map[ENGLISH] = "英文"

def language_check(query):
    """直接通过是否包含中文字符来判断
    Args:
        query (_type_): _description_

    Returns:
        _type_: _description_
    """
    r = re.findall('[\u4e00-\u9fff]+', query)
    if not r:
        return ENGLISH 
    else:
        return CHINESE


def is_api_query(query)-> bool:
    """
    Args:
        query (_type_): _description_

    Returns:
        bool: _description_
    """
    return 'api' in query.lower()


def is_query_too_short(query:str,threshold=3):
    tokenizer = BasicTokenizer()
    return len(tokenizer.tokenize(query)) <= threshold



class Translator:
    client = None

    @staticmethod
    def get_client():
        client = boto3.client('translate')
        return client

    @classmethod
    def translate(cls,query,source_lang,target_lang):
        """

        Args:
            query (_type_): _description_
            source_lang (_type_): _description_
            target_lang (_type_): _description_
        """
        if cls.client is None:
            cls.client = cls.get_client()
        
        r = cls.client.translate_text(
            Text=query,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        return r['TranslatedText']

class LLMTranslator:
    def __init__(self,model_id,model_kwargs=None,**kwargs) -> None:
        self.translate_chain =  LLMChain.get_chain(
            model_id,intent_type=QUERY_TRANSLATE_TYPE,
            model_kwargs=model_kwargs,
            **kwargs
        )
       
    def translate(self,query,source_lang,target_lang):
        """
        Args:
            query (_type_): _description_
            source_lang (_type_): _description_
            target_lang (_type_): _description_
        """
        r = self.translate_chain.invoke({"query":query,"target_lang":language_text_map[target_lang]})
        return r

def query_translate(query,lang,translate_config:dict):
    source_lang = lang 

    if lang == CHINESE:
        target_lang = ENGLISH
    else:
        target_lang = CHINESE

    model_id = translate_config['model_id']
    if model_id == AWS_TRANSLATE_SERVICE_MODEL_ID:
        translated_text = Translator.translate(
            query,source_lang,target_lang
        )
    elif model_id == QUERY_TRANSLATE_IDENTITY_TYPE:
        return query
    else:
        translated_text = LLMTranslator(
        **translate_config
    ).translate(
        query,source_lang,target_lang
    )
    
    return translated_text

def run_preprocess(query):
    """
    1. whether API's query.
    2. Language check.
    3. query translate

    Args:
        text (_type_): _description_
    """
    is_api = is_api_query(query)
    query_lang = language_check(query)

    translated_text = query_translate(query,lang=query_lang)

    service_names = get_service_name(query)

    ret = {
        'query':query,
        'is_api_query': is_api,
        'translated_text': translated_text,
        'query_lang':query_lang,
        'service_names': service_names
    }

    return ret  


