from ragas.metrics import ContextRecall
import typing as t
from langchain.callbacks.manager import CallbackManager, trace_as_chain_group
from datasets import Dataset
from llm_model import Claude21
import re

CLAUDE_CONTEXT_RECALL_RA ="""\n\nHuman:
Given a question wrapped with  <question></question> tag, a context wrapped with  <context></context> tag, and an answer wrapped with  <answer></answer> tag, analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not. Output json with reason wrapped with <classification></classification> tag.
The following context wrapped with <example></example> tag are two examples.

<example index="1">
<question>
What can you tell me about albert Albert Einstein?
</question>

<context>
Albert Einstein (14 March 1879 – 18 April 1955) was a German-born theoretical physicist,widely held to be one of the greatest and most influential scientists of all time. Best known for developing the theory of relativity, he also made important contributions to quantum mechanics, and was thus a central figure in the revolutionary reshaping of the scientific understanding of nature that modern physics accomplished in the first decades of the twentieth century. His mass–energy equivalence formula E = mc2, which arises from relativity theory, has been called "the world's most famous equation". He received the 1921 Nobel Prize in Physics "for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect", a pivotal step in the development of quantum theory. His work is also known for its influence on the philosophy of science. In a 1999 poll of 130 leading physicists worldwide by the British journal Physics World, Einstein was ranked the greatest physicist of all time. His intellectual achievements and originality have made Einstein synonymous with genius.
</context>

<answer>
Albert Einstein born in 14 March 1879 was  German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time. He received the 1921 Nobel Prize in Physics "for his services to theoretical physics. He published 4 papers in 1905.  Einstein moved to Switzerland in 1895 
</answer>

Here is my classification:
<classification>
[
    {{  "statement_1":"Albert Einstein, born on 14 March 1879, was a German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time.",
        "reason": "The date of birth of Einstein is mentioned clearly in the context.",
        "Attributed": "Yes"
    }},
    {{
        "statement_2":"He received the 1921 Nobel Prize in Physics 'for his services to theoretical physics.",
        "reason": "The exact sentence is present in the given context.",
        "Attributed": "Yes"
    }},
    {{
        "statement_3": "He published 4 papers in 1905.",
        "reason": "There is no mention about papers he wrote in the given context.",
        "Attributed": "No"
    }},
    {{
        "statement_4":"Einstein moved to Switzerland in 1895.",
        "reason": "There is no supporting evidence for this in the given context.",
        "Attributed": "No"
    }}
]
</classification>
</example>


<example index="2">
<question>
who won 2020 icc world cup?
</question>

<context> Who won the 2022 ICC Men's T20 World Cup?
The 2022 ICC Men's T20 World Cup, held from October 16 to November 13, 2022, in Australia, was the eighth edition of the tournament. Originally scheduled for 2020, it was postponed due to the COVID-19 pandemic. England emerged victorious, defeating Pakistan by five wickets in the final to clinch their second ICC Men's T20 World Cup title.
</context>


<answer>
England 
</answer>

Here is my classification:
<classification>
[
    {{
        "statement_1":"England won the 2022 ICC Men's T20 World Cup.",
        "reason": "From context it is clear that England defeated Pakistan to win the World Cup.",
         "Attributed": "Yes"
    }}
]
</classification>
</example>

<question>
{question}
</question>

<context>
{context}
</context>

<answer>
{answer}
</answer>

\n\nAssistant:
Here is my classification:
<classification>
[
"""

class ClaudeContextRacall(ContextRecall):
    def _score_batch_helper(
        self,
        dataset: Dataset,
        callbacks =  None,
        callback_group_name: str = "batch",
    ) -> list:
        prompts = []
        question, ground_truths, contexts = (
            dataset["question"],
            dataset["ground_truths"],
            dataset["contexts"],
        )

        for qstn, gt, ctx in zip(question, ground_truths, contexts):
            
            gt = "\n".join(gt) if isinstance(gt, list) else gt
            ctx = "\n".join(ctx) if isinstance(ctx, list) else ctx
    
            prompt = CLAUDE_CONTEXT_RECALL_RA.format(
                question=qstn, context=ctx, answer=gt
            )
            prompts.append(prompt)

        responses: list[str] = []
        for prompt in prompts:
            r = Claude21.generate(
                prompt=prompt,
                use_default_prompt_template=False,
                temperature=0.0
            )
            # parser result
            r  = '<classification>\n[' + r 
            rets = re.findall('<classification>(.*?)</classification>',r,re.S)
            rets = [ret.strip() for ret in rets]
            if not rets and len(rets) > 1:
                raise RuntimeError(f'invalid claude generation,prompt:\n{prompt}, \noutput: {r}')
            responses.append((prompt,rets[0]))

        scores = []
        for prompt,res in responses:
            try:
                response = eval(res)
                denom = len(response)
                numerator = sum(
                    item.get("Attributed").lower() == "yes" for item in response
                )
                scores.append(numerator / denom)
            except:
                raise RuntimeError(f'invalid claude generation,prompt:\n{prompt}, \noutput: {res}')
            
        return scores
    
    def _score_batch(
            self,
            dataset: Dataset,
            callbacks =  None,
            callback_group_name: str = "batch"
    ) -> list:
        return self._score_batch_helper(
            dataset=dataset,
            callbacks=callbacks,
            callback_group_name=callback_group_name
        )

context_recall = ClaudeContextRacall()