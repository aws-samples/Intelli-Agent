import typing as t
from datasets import Dataset
from llm_model import Claude21
import re

from langchain.embeddings import BedrockEmbeddings
from ragas.metrics import AnswerRelevancy


CLAUDE_QUESTION_GEN="""\n\nHuman:
Generate question wrapped with  <question></question> tag for the given answer  wrapped with  <answer></answer> tag.
The following context wrapped with <example></example> tag is an example.

<answer>
The PSLV-C56 mission is scheduled to be launched on Sunday, 30 July 2023 at 06:30 IST / 01:00 UTC. It will be launched from the Satish Dhawan Space Centre, Sriharikota, Andhra Pradesh, India 
</answer>

<question>
When is the scheduled launch date and time for the PSLV-C56 mission, and where will it be launched from?
</question>


<answer>
{answer}
</answer>

\n\nAssistant:
<question>
"""



class ClaudeAnswerRelevancy(AnswerRelevancy):
    embeddings = BedrockEmbeddings()

    def _score_batch(
        self,
        dataset: Dataset,
        callbacks = None,
        callback_group_name: str = "batch",
    ) -> list[float]:
        questions, answers = dataset["question"], dataset["answer"]
       
        results = []
        for ans in answers:
            human_prompt = CLAUDE_QUESTION_GEN.format(answer=ans)
            _questions = []
            for _ in range(self.strictness):
                r = Claude21.generate(
                    prompt=human_prompt,
                    use_default_prompt_template=False
                )
                r  = '<question>' + r 
                rets = re.findall('<question>(.*?)</question>',r,re.S)
                rets = [ret.strip() for ret in rets]
                if not rets and len(rets) > 1:
                    raise RuntimeError(f'invalid claude generation,prompt:\n{human_prompt}, \noutput: {r}')
                _questions.append(rets[0])

            results.append(_questions)
        
        scores = []
        for question, gen_questions in zip(questions, results):
            cosine_sim = self.calculate_similarity(question, gen_questions)
            scores.append(cosine_sim.mean())

        return scores


answer_relevancy = ClaudeAnswerRelevancy()
