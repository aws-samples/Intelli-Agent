import sys
import os
from functools import partial

sys.path.append("./common_logic")
sys.path.append("../job/dep/llm_bot_dep")
from dotenv import load_dotenv
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__),'.env')
)
import json
import time 
import common_logic.common_utils.websocket_utils as websocket_utils
from common_logic.common_utils.constant import LLMTaskType

class DummyWebSocket:
    def post_to_connection(self,ConnectionId,Data):
        data = json.loads(Data)
        ret = data
        message_type = ret['message_type']
        # print('message_type',message_type)
        if message_type == "START":
            pass
        elif message_type == "CHUNK":
            print(ret['message']['content'],end="",flush=True)
        elif message_type == "END":
            return 
        elif message_type == "ERROR":
            print(ret['message']['content'])
            return 
        elif message_type == "MONITOR":
            if ret['message'].strip():
                print("monitor info: ",ret['message'])

websocket_utils.ws_client = DummyWebSocket()

from common_logic.common_utils.lambda_invoke_utils import invoke_lambda

def generate_answer(query,
                    entry_type="common",
                    stream=False,
                    session_id=None,
                    chatbot_config=None
                    ):
    chatbot_config = chatbot_config or {}
    session_id = session_id or time.time()

    body = {
            "query": query,
            "entry_type": entry_type,
            "session_id":session_id,
            "chatbot_config": chatbot_config     
            }
    event = {
        "body": json.dumps(body)
    }
    if stream:
        event["requestContext"] = {
            "eventType":"MESSAGE",
            "connectionId":f'test_{int(time.time())}'
        }
    response = invoke_lambda(
        lambda_invoke_mode="local",
        lambda_module_path="lambda_main.main",
        event_body=event
    )
    # response = main.lambda_handler(event, context)
    if stream:
        return
    if not stream:
        body = json.loads(response["body"])
        # print(body)
        return body


class SimilarityCalculateText2Vec:
    """use text2vec package to calculate sentence similarity
    """
    instance = {}
    
    @classmethod
    def create_model_tencent(cls,**kwargs):
        model_name = kwargs.pop('model_name')
        encode_kwargs = kwargs.pop('encode_kwargs',{})
        if model_name  in cls.instance:
            return cls.instance[model_name]
        from text2vec import SentenceModel, Word2Vec
        w2v_model = Word2Vec(**kwargs)
        model = partial(w2v_model.encode,**encode_kwargs)
        cls.instance[model_name] = model
        return model

    @classmethod
    def create_model(cls,**kwargs):
        model_name = kwargs.get("model_name","tencent")
        return getattr(cls,f"create_model_{model_name}")(**kwargs)


def similarity_calculate(sentence1,sentence2,model_name="tencent",**kwargs):
    model = SimilarityCalculateText2Vec.create_model(
        model_name=model_name,
        **kwargs
    )
    ret = model([sentence1,sentence2])
    from text2vec import cos_sim
    return cos_sim(ret[0],ret[1]).tolist()[0][0]



def auto_evaluation_with_claude(ref_answer,model_answer,llm_config=None,examples=""):
    if llm_config is None:
        llm_config = {
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
        }
    output:float = invoke_lambda(
                lambda_name='Online_LLM_Generate',
                lambda_module_path="lambda_llm_generate.llm_generate",
                handler_name='lambda_handler',
                event_body={
                    "llm_config": {
                        **llm_config, 
                          "intent_type": LLMTaskType.AUTO_EVALUATION
                        },
                    "llm_input": {
                        "ref_answer":ref_answer,
                         "model_answer":model_answer
                         }
                    }
            )
    return output


def test_auto_evaluation_with_claude():
    ref_answer = """非常抱歉给您带来这么大的麻烦，等收到您的退货商品后安排退款给您"""
    model_answer = """非常抱歉给您带来了不愉快的体验，我们已经反馈给仓库，他们将对此进行核实并改进。对于您的订单，我们将尽快处理退货事宜，您不需要承担任何运费。请在后台申请退货，我将为您备注。再次为给您带来的不便道歉，感谢您的理解。"""
    
    r = auto_evaluation_with_claude(
        ref_answer=ref_answer,
        model_answer=model_answer
    )
    print(r)
    
def test_similarity_calculate():
    sentence1 = "如何更换花呗绑定银行卡"
    sentence2 = '花呗更改绑定银行卡'
    print(similarity_calculate(sentence1=sentence1,sentence2=sentence2))
    print(similarity_calculate(sentence1=sentence1,sentence2=sentence2))
    print(similarity_calculate(sentence1=sentence1,sentence2=sentence2))
    


if __name__ == "__main__":
    test_auto_evaluation_with_claude()
    








