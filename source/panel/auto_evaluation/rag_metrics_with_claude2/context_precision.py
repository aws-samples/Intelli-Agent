from ragas.metrics import ContextPrecision
import typing as t
from langchain.callbacks.manager import CallbackManager, trace_as_chain_group
from datasets import Dataset
from llm_model import Claude21
import re
from utils.llm_utils.llm_models import Model
from langchain.prompts import ChatPromptTemplate
# from llm_model import Claude21

claude_model =  Model.get_model(
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0",
    model_kwargs={
        "max_tokens": 10000,
        "temperature": 0.1
    }
)



CLAUDE_CONTEXT_PRECISION = """Given a question wrapped with  <question></question> tag, and a context wrapped with  <context></context> tag, verify if the information in the given context is useful in answering the question. Return a Yes/No answer wrapped with  <answer></answer> tag.
<question>
{question}
</question>

<context>
{context}
</context>

Return a Yes/No answer wrapped with  <answer></answer> tag.
"""

precision_prompt_template = ChatPromptTemplate.from_messages([
    ('user',CLAUDE_CONTEXT_PRECISION)
])
class ClaudeContextprecision(ContextPrecision):

    def _score_batch(
        self,
        dataset: Dataset,
        callbacks: t.Optional[CallbackManager] = None,
        callback_group_name: str = "batch",
    ) -> list:
        prompts = []
        questions, contexts = dataset["question"], dataset["contexts"]
        
        for qstn, ctx in zip(questions, contexts):
            human_prompts = [
                CLAUDE_CONTEXT_PRECISION.format(
                    question=qstn,
                    context=c
                )
                for c in ctx
            ]
            prompts.append(human_prompts)
        
        responses: list[list[str]] = []
        for human_prompts in prompts:
            response = []
            for prompt in human_prompts:
                r = Claude21.generate(
                    prompt=prompt,
                    use_default_prompt_template=False
                )
                r  = '<answer>' + r 
                rets = re.findall('<classification>(.*?)</classification>',r,re.S)
                rets = [ret.strip() for ret in rets]
                if not rets and len(rets) > 1:
                    raise RuntimeError(f'invalid claude generation,prompt:\n{prompt}, \noutput: {r}')
                response.append(r)
            responses.append(response)
            
        scores = []

        for response in responses:
            response = [1 if "yes" in resp.lower() else 0 for resp in response]
            # response = [int(any("yes" in r.lower() for r in resp)) for resp in response]
            denominator = sum(response) + 1e-10
            numerator = sum(response)
        
            scores.append(numerator / denominator)

        return scores


context_precision = ClaudeContextprecision()