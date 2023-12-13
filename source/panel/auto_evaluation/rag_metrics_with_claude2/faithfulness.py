from ragas.metrics import Faithfulness
import typing as t
from langchain.callbacks.manager import CallbackManager, trace_as_chain_group
from datasets import Dataset
from llm_model import Claude21
import re


# find statments from answer
CLAUDE_LONG_FORM_ANSWER_PROMPT = """\n\nHuman:
Given a question wrapped with <question></question> tag and answer wrapped with <answer></answer> tag, create one or more statements wrapped with <statements></statements> tag from each sentence in the given answer.
The following context wrapped with <example></example> tag are three examples.

<example index="1">
<question>
Who was  Albert Einstein and what is he best known for?
</question>

<answer>
He was a German-born theoretical physicist, widely acknowledged to be one of the greatest and most influential physicists of all time. He was best known for developing the theory of relativity, he also made important contributions to the development of the theory of quantum mechanics.
</answer>

<statements>
\nAlbert Einstein was born in Germany.\nAlbert Einstein was best known for his theory of relativity.
</statements>
</example>

<example index="2">
<question>
Cadmium Chloride is slightly soluble in this chemical, it is also called what?
</question>

<answer>
alcohol
</answer>

<statements>
\nCadmium Chloride is slightly soluble in alcohol.
</statements>
</example>

<example index="3">
<question>
Were Shahul and Jithin of the same nationality?

<answer>
They were from different countries.
</answer>

<statements>
\nShahul and Jithin were from different countries.
</statements>
</example>


<question>
{question}
</question>

<answer>
{answer}
</answer>

\n\nAssistant:
<statements>\n"""


CLAUDE_NLI_STATEMENTS_MESSAGE = """\n\nHuman:
Consider the given context  wrapped with <context></context> and following statements wrapped with <statements></statements>, then determine whether they are supported by the information present in the context.Provide a brief explanation for each statement before arriving at the verdict (Yes/No). Provide a final verdict for each statement in order at the end in the given format. Do not deviate from the specified format.
The following context wrapped with <example></example> tag is an example.

<context>
John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
</context>

<statements>
1. John is majoring in Biology.\n2. John is taking a course on Artificial Intelligence.\n3. John is a dedicated student.\n4. John has a part-time job.\n5. John is interested in computer programming.\n
</statements>

<answer>
1. John is majoring in Biology.
Explanation: John's major is explicitly mentioned as Computer Science. There is no information suggesting he is majoring in Biology.  Verdict: No.
2. John is taking a course on Artificial Intelligence.
Explanation: The context mentions the courses John is currently enrolled in, and Artificial Intelligence is not mentioned. Therefore, it cannot be deduced that John is taking a course on AI. Verdict: No.
3. John is a dedicated student.
Explanation: The prompt states that he spends a significant amount of time studying and completing assignments. Additionally, it mentions that he often stays late in the library to work on his projects, which implies dedication. Verdict: Yes.
4. John has a part-time job.
Explanation: There is no information given in the context about John having a part-time job. Therefore, it cannot be deduced that John has a part-time job.  Verdict: No.
5. John is interested in computer programming.
Explanation: The context states that John is pursuing a degree in Computer Science, which implies an interest in computer programming. Verdict: Yes.
Final verdict for each statement in order: No. No. Yes. No. Yes.
</answer>

<context>
{context}
</context>

<statements>
{statements}
</statements>

\n\nAssistant:
<answer>\n
"""  # noqa: E501


class ClaudeFaithfulness(Faithfulness):
    def _score_batch(
        self,
        ds: Dataset,
        callbacks: t.Optional[CallbackManager] = None,
        callback_group_name: str = "batch",
    ) -> list[float]:
        """
        returns the NLI score for each (q, c, a) pair
        """

        question, answer, contexts = ds["question"], ds["answer"], ds["contexts"]
        prompts = []
        list_statements: list[list[str]] = []
        
        for q, a in zip(question, answer):
            human_prompt = CLAUDE_LONG_FORM_ANSWER_PROMPT.format(question=q, answer=a)
            prompts.append(human_prompt)
            r = Claude21.generate(
             prompt=human_prompt,
             use_default_prompt_template=False,
            )
            r = '<statements>\n' + r 
            rets = re.findall('<statements>(.*?)</statements>',r,re.S)
            rets = [ret.strip() for ret in rets]
            if not rets and len(rets) > 1:
                raise RuntimeError(f'invalid claude generation,prompt:\n{human_prompt}, \noutput: {r}')
            statements = rets[0].split("\n")
            list_statements.append(statements)

        
        outputs = []
        for context, statements in zip(contexts, list_statements):
            statements_str: str = "\n".join(
                [f"{i+1}.{st}" for i, st in enumerate(statements)]
            )
            contexts_str: str = "\n".join(context)
            human_prompt = CLAUDE_NLI_STATEMENTS_MESSAGE.format(
                context=contexts_str, statements=statements_str
            )
            r = Claude21.generate(
             prompt=human_prompt,
             use_default_prompt_template=False,
            )
            r = '<answer>\n' + r 
            rets = re.findall('<answer>(.*?)</answer>',r,re.S)
            rets = [ret.strip() for ret in rets]
            if not rets and len(rets) > 1:
                raise RuntimeError(f'invalid claude generation,prompt:\n{human_prompt}, \noutput: {r}')
            outputs.append(rets[0])

        scores = []
        final_answer = "Final verdict for each statement in order:"
        final_answer = final_answer.lower()
        for i, output in enumerate(outputs):
            output = output.lower().strip()
            if final_answer in output:
                output = output[output.find(final_answer) + len(final_answer) :]
                score = sum(
                    0 if "yes" in answer else 1
                    for answer in output.strip().split(".")
                    if answer != ""
                )
                score = score / len(list_statements[i])
            else:
                score = max(0, output.count("verdict: no")) / len(
                    list_statements[i]
                )

            scores.append(1 - score)

        return scores


faithfulness = ClaudeFaithfulness()
