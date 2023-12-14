import typing as t
from datasets import Dataset
from llm_model import Claude21
import re
import numpy as np

from ragas.metrics import ContextRelevancy as _ContextRelevancy
from ragas.metrics._context_relevancy import sent_tokenize


CLAUDE_CONTEXT_RELEVANCE = """\n\nHuman:
Please extract relevant sentences wrapped with  <sentences></sentences> tag from the provided context wrapped with <context></context> tag, that is absolutely required answer the following question wrapped with  <question></question> tag. If no relevant sentences are found, or if you believe the question cannot be answered from the given context, return the phrase "Insufficient Information".  While extracting candidate sentences you're not allowed to make any changes to sentences from given context.

<question>
{question}
</question>

<context>
{context}
</context>

\n\nAssistant:
<sentences>
"""


class ContextRelevancy(_ContextRelevancy):
    def _score_batch(
        self,
        dataset: Dataset,
        callbacks = None,
        callback_group_name= "batch",
    ) -> list[float]:
        questions, contexts = dataset["question"], dataset["contexts"]
        responses: list[str] = []

        for q,c in zip(questions, contexts):
            human_prompt = CLAUDE_CONTEXT_RELEVANCE.format(
                question=q, context="\n".join(c)
            )
            r = Claude21.generate(
                    prompt=human_prompt,
                    use_default_prompt_template=False
                )
            r  = '<sentences>' + r
            rets = re.findall('<sentences>(.*?)</sentences>',r,re.S)
            rets = [ret.strip() for ret in rets]
            
            if not rets and len(rets) > 1:
                raise RuntimeError(f'invalid claude generation,prompt:\n{human_prompt}, \noutput: {r}')

            responses.append([rets[0]])
        

        print(responses)
        scores = []
        for context, n_response in zip(contexts, responses):
            context = "\n".join(context)
            overlap_scores = []
            context_sents = sent_tokenize(context)
            for output in n_response:
                indices = (
                    sent_tokenize(output.strip())
                    if output.lower() != "insufficient information."
                    else []
                )
                if len(context_sents) == 0:
                    score = 0
                else:
                    score = min(len(indices) / len(context_sents), 1)
                overlap_scores.append(score)
            scores.append(np.mean(overlap_scores))

        return scores


context_relevancy = ContextRelevancy()