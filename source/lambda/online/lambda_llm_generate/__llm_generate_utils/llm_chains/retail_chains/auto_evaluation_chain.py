# auto evaluation based on llms
import re

from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain_core.messages import AIMessage,SystemMessage,HumanMessage
from common_logic.common_utils.logger_utils import get_logger
from langchain.prompts import ChatPromptTemplate,HumanMessagePromptTemplate
from langchain_core.messages import convert_to_messages
from common_logic.common_utils.constant import (
    MessageType,
    LLMTaskType,
    LLMModelType,
)
from ...llm_models import Model
from ..llm_chain_base import LLMChain

from ..chat_chain import Claude2ChatChain

logger = get_logger("auto_evaluation")

AUTO_EVALUATION_TEMPLATE = """作为一位专业的评分员,您需要根据以下标准对模型的回答进行公正、客观的评分,并提供有价值的反馈意见,以帮助模型持续改进。

### 评分标准

- 满分为10分,最低分为1分, 分值为一个 float 类型。
- 模型回答与标准答案的相关性越高,得分越高。
- 如果模型的回答出现大量重复内容，可以直接给0分。
- 除了内容相关性,还需考虑回答的完整性、逻辑性和语言表达。
- 请先在xml 标签 <thinking> 和 </thinking> 中写下你的评分理由。
- 最后在 xml 标签 <score> 和 </score> 中写下你的最终评分。

### 示例评分
{examples}

### 评分上下文

标准答案: 
<ground_truth>
{ref_answer}
</ground_truth>

模型回答: 
<model_answer>
{model_answer}
</model_answer>

请根据上述标准和上下文,对模型的回答进行评分并提供反馈意见。让我们一起努力,提高模型的表现!
"""


class Claude2AutoEvaluationChain(Claude2ChatChain):
    intent_type = LLMTaskType.AUTO_EVALUATION  
    model_id = LLMModelType.CLAUDE_2

    @classmethod
    def create_messages(cls,x:dict,examples=""):
        prompt = AUTO_EVALUATION_TEMPLATE.format(
            ref_answer=x['ref_answer'],
            model_answer=x['model_answer'],
            examples=examples
        )
        messages = [
            HumanMessage(content=prompt),
            AIMessage(content="<thinking>")
            ]
        return messages

    @classmethod
    def postprocess(cls,content):
        logger.info(f"auto eval content: {content}")
        try:
            score = float(re.findall("<score>(.*?)</score>",content)[0].strip())
            return score
        except Exception as e:
            logger.error(f"error: {e}, content: {content}")
            raise e
            

    @classmethod
    def create_chain(cls, model_kwargs=None, **kwargs):
        llm = Model.get_model(cls.model_id, model_kwargs=model_kwargs, **kwargs)
        chain = RunnableLambda(lambda x: cls.create_messages(x)) | llm | RunnableLambda(lambda x: cls.postprocess(x.content))
        return chain  
        

class Claude21AutoEvaluationChain(Claude2AutoEvaluationChain):
    model_id = LLMModelType.CLAUDE_21



class Claude3HaikuAutoEvaluationChain(Claude2AutoEvaluationChain):
    model_id = LLMModelType.CLAUDE_3_HAIKU


class Claude3SonnetAutoEvaluationChain(Claude2AutoEvaluationChain):
    model_id = LLMModelType.CLAUDE_3_SONNET



