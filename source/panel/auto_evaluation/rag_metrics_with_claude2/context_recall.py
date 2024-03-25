from ragas.metrics import ContextRecall
import typing as t
from langchain.callbacks.manager import CallbackManager, trace_as_chain_group
from datasets import Dataset
import re

import xml.etree.ElementTree as ET
# from langchain.chat_models.bedrock import BedrockChat

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



# CLAUDE_CONTEXT_RECALL_RA ="""Given a question wrapped with  <question></question> tag, a context wrapped with  <context></context> tag, and an answer wrapped with  <answer></answer> tag, analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not. Output json with reason wrapped with <classification></classification> tag.
# The following context wrapped with <example></example> tag are two examples.

# <example index="1">
# <question>
# What can you tell me about albert Albert Einstein?
# </question>

# <context>
# Albert Einstein (14 March 1879 – 18 April 1955) was a German-born theoretical physicist,widely held to be one of the greatest and most influential scientists of all time. Best known for developing the theory of relativity, he also made important contributions to quantum mechanics, and was thus a central figure in the revolutionary reshaping of the scientific understanding of nature that modern physics accomplished in the first decades of the twentieth century. His mass–energy equivalence formula E = mc2, which arises from relativity theory, has been called "the world's most famous equation". He received the 1921 Nobel Prize in Physics "for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect", a pivotal step in the development of quantum theory. His work is also known for its influence on the philosophy of science. In a 1999 poll of 130 leading physicists worldwide by the British journal Physics World, Einstein was ranked the greatest physicist of all time. His intellectual achievements and originality have made Einstein synonymous with genius.
# </context>

# <answer>
# Albert Einstein born in 14 March 1879 was  German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time. He received the 1921 Nobel Prize in Physics "for his services to theoretical physics. He published 4 papers in 1905.  Einstein moved to Switzerland in 1895 
# </answer>

# Here is my classification:
# <classification>
# [
#     {{  "statement_1":"Albert Einstein, born on 14 March 1879, was a German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time.",
#         "reason": "The date of birth of Einstein is mentioned clearly in the context.",
#         "Attributed": "Yes"
#     }},
#     {{
#         "statement_2":"He received the 1921 Nobel Prize in Physics 'for his services to theoretical physics.",
#         "reason": "The exact sentence is present in the given context.",
#         "Attributed": "Yes"
#     }},
#     {{
#         "statement_3": "He published 4 papers in 1905.",
#         "reason": "There is no mention about papers he wrote in the given context.",
#         "Attributed": "No"
#     }},
#     {{
#         "statement_4":"Einstein moved to Switzerland in 1895.",
#         "reason": "There is no supporting evidence for this in the given context.",
#         "Attributed": "No"
#     }}
# ]
# </classification>
# </example>


# <example index="2">
# <question>
# who won 2020 icc world cup?
# </question>

# <context> Who won the 2022 ICC Men's T20 World Cup?
# The 2022 ICC Men's T20 World Cup, held from October 16 to November 13, 2022, in Australia, was the eighth edition of the tournament. Originally scheduled for 2020, it was postponed due to the COVID-19 pandemic. England emerged victorious, defeating Pakistan by five wickets in the final to clinch their second ICC Men's T20 World Cup title.
# </context>


# <answer>
# England 
# </answer>

# Here is my classification:
# <classification>
# [
#     {{
#         "statement_1":"England won the 2022 ICC Men's T20 World Cup.",
#         "reason": "From context it is clear that England defeated Pakistan to win the World Cup.",
#         "Attributed": "Yes"
#     }}
# ]
# </classification>
# </example>

# <question>
# {question}
# </question>

# <context>
# {context}
# </context>

# <answer>
# {answer}
# </answer>
# """

# CLAUDA_CONTEXT_RECALL_RA= """Given a context, and an answer, analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not. Output JSON with reason.
# Here are some examples of ideal JSON formatting:


# question: What can you tell me about albert Albert Einstein?
# context: Albert Einstein (14 March 1879 – 18 April 1955) was a German-born theoretical physicist,widely held to be one of the greatest and most influential scientists of all time. Best known for developing the theory of relativity, he also made important contributions to quantum mechanics, and was thus a central figure in the revolutionary reshaping of the scientific understanding of nature that modern physics accomplished in the first decades of the twentieth century. His mass–energy equivalence formula E = mc2, which arises from relativity theory, has been called "the world's most famous equation". He received the 1921 Nobel Prize in Physics "for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect", a pivotal step in the development of quantum theory. His work is also known for its influence on the philosophy of science. In a 1999 poll of 130 leading physicists worldwide by the British journal Physics World, Einstein was ranked the greatest physicist of all time. His intellectual achievements and originality have made Einstein synonymous with genius.
# answer: Albert Einstein born in 14 March 1879 was  German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time. He received the 1921 Nobel Prize in Physics "for his services to theoretical physics. He published 4 papers in 1905.  Einstein moved to Switzerland in 1895 
# classification:
# [
#     {{  "statement_1":"Albert Einstein, born on 14 March 1879, was a German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time.",
#         "reason": "The date of birth of Einstein is mentioned clearly in the context.",
#         "Attributed": "Yes"
#     }},
#     {{
#         "statement_2":"He received the 1921 Nobel Prize in Physics 'for his services to theoretical physics.",
#         "reason": "The exact sentence is present in the given context.",
#         "Attributed": "Yes"
#     }},
#     {{
#         "statement_3": "He published 4 papers in 1905.",
#         "reason": "There is no mention about papers he wrote in the given context.",
#         "Attributed": "No"
#     }},
#     {{
#         "statement_4":"Einstein moved to Switzerland in 1895.",
#         "reason": "There is no supporting evidence for this in the given context.",
#         "Attributed": "No"
#     }}
# ]

# question: who won 2020 icc world cup?
# context: Who won the 2022 ICC Men's T20 World Cup?
# The 2022 ICC Men's T20 World Cup, held from October 16 to November 13, 2022, in Australia, was the eighth edition of the tournament. Originally scheduled for 2020, it was postponed due to the COVID-19 pandemic. England emerged victorious, defeating Pakistan by five wickets in the final to clinch their second ICC Men's T20 World Cup title.
# answer: England 
# classification:
# [
#     {{
#         "statement_1":"England won the 2022 ICC Men's T20 World Cup.",
#         "reason": "From context it is clear that England defeated Pakistan to win the World Cup.",
#          "Attributed": "Yes"
#     }}
# ]


# Now, given a  context, and answer, please analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not, following the formatting of the examples above.

# question:{question}
# context:{context}
# answer:{answer}
# """


CLAUDA_CONTEXT_RECALL_RA= """Given a question wrappered with <question></question> ,a context wrappered with <context></context> tag, and an answer wrappered with <answer></answer> tag, analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not. Output XML with reason.
Here are some examples of ideal XML formatting:

<question>
What can you tell me about albert Albert Einstein?
</question>

<context>
Albert Einstein (14 March 1879 – 18 April 1955) was a German-born theoretical physicist,widely held to be one of the greatest and most influential scientists of all time. Best known for developing the theory of relativity, he also made important contributions to quantum mechanics, and was thus a central figure in the revolutionary reshaping of the scientific understanding of nature that modern physics accomplished in the first decades of the twentieth century. His mass–energy equivalence formula E = mc2, which arises from relativity theory, has been called "the world's most famous equation". He received the 1921 Nobel Prize in Physics "for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect", a pivotal step in the development of quantum theory. His work is also known for its influence on the philosophy of science. In a 1999 poll of 130 leading physicists worldwide by the British journal Physics World, Einstein was ranked the greatest physicist of all time. His intellectual achievements and originality have made Einstein synonymous with genius.
</context>

<answer>
Albert Einstein born in 14 March 1879 was  German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time. He received the 1921 Nobel Prize in Physics "for his services to theoretical physics. He published 4 papers in 1905.  Einstein moved to Switzerland in 1895 
</answer>

<classification>
    <classify>
        <statement>
        Albert Einstein, born on 14 March 1879, was a German-born theoretical physicist, widely held to be one of the greatest and most influential scientists of all time.
        </statement>
        <reason>
        The date of birth of Einstein is mentioned clearly in the context.
        </reason>
        <Attributed>
        Yes
        </Attributed>
    </classify>

    <classify>
        <statement>
        He received the 1921 Nobel Prize in Physics 'for his services to theoretical physics.
        </statement>
        <reason>
        The exact sentence is present in the given context.
        </reason>
        <Attributed>
        Yes
        </Attributed>
    </classify>

    <classify>
        <statement>
        He published 4 papers in 1905.
        </statement>
        <reason>
        There is no mention about papers he wrote in the given context.
        </reason>
        <Attributed>
        No
        </Attributed>
    </classify>

    <classify>
        <statement>
        Einstein moved to Switzerland in 1895.
        </statement>
        <reason>
        There is no supporting evidence for this in the given context.
        </reason>
        <Attributed>
        No
        </Attributed>
    </classify>
</classification>


<question>
who won 2020 icc world cup?
</question>

<context>
Who won the 2022 ICC Men's T20 World Cup?
The 2022 ICC Men's T20 World Cup, held from October 16 to November 13, 2022, in Australia, was the eighth edition of the tournament. Originally scheduled for 2020, it was postponed due to the COVID-19 pandemic. England emerged victorious, defeating Pakistan by five wickets in the final to clinch their second ICC Men's T20 World Cup title.
</context>

<answer>
England 
</answer>

<classification>
    <classify>
        <statement>
        England won the 2022 ICC Men's T20 World Cup.
        </statement>
        <reason>
        From context it is clear that England defeated Pakistan to win the World Cup.
        </reason>
        <Attributed>
        Yes
        </Attributed>
    </classify>

</classification>


Now, given a new context, and answer, please analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not, following the formatting of the examples above.

<question>
{question}
</question>

<context>
{context}
</context>

<answer>
{answer}
</answer>
"""




# to_assistant_mouth = """classification:"""

recall_prompt_template = ChatPromptTemplate.from_messages(
    [
        ('user', CLAUDA_CONTEXT_RECALL_RA),
        # ('assistant', to_assistant_mouth)
    ]

)


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
        data = []
        for qstn, gt, ctx in zip(question, ground_truths, contexts):
            
            gt = "\n".join(gt) if isinstance(gt, list) else gt
            ctx = "\n".join(ctx) if isinstance(ctx, list) else ctx
            data.append({
                "question":qstn,
                "context": ctx,
                "answer": gt
            })
    
            # prompt = CLAUDE_CONTEXT_RECALL_RA.format(
            #     question=qstn, context=ctx, answer=gt
            # )
            # prompts.append(prompt)

        responses: list[str] = []
        for datum in data:
            prompt = str(recall_prompt_template.invoke(datum))
            r = (recall_prompt_template | claude_model).invoke(datum).content

            # pattern = "\[\s*\{.*?\}(\s*,\s*\{.*?\})*\s*\]"
            # match = re.search(pattern, r.replace("\n", ""))

            # if not match:
            #     raise RuntimeError(f'invalid claude generation,prompt:\n{prompt} \noutput: {r}')

            # r = eval(r[0])
            # denom = len(r)
            # numerator = sum(
            #     item.get("Attributed").lower() == "yes" for item in response
            # )
            # scores.append(numerator / denom)
      
            responses.append((prompt, r))
          
            # r = Claude3Sonne.generate(
            #     prompt=prompt,
            #     use_default_prompt_template=False,
            #     temperature=0.0
            # )

            # parser result
            # r1  = '<classification>\n[' + r 
            # rets = re.findall('<classification>(.*?)</classification>',r1,re.S)
            # rets = [ret.strip() for ret in rets]
            # if not rets and len(rets) > 1:
            #     # rets = re.findall('<classification>(.*?)</classification>',r,re.S)
            #     # if not rets and len(rets) > 1:
            #     raise RuntimeError(f'invalid claude generation,prompt:\n{prompt}, \noutput: {r}')
            # responses.append((prompt,rets[0]))

        scores = []
        for prompt,res in responses:
            try:
                # r = re.findall('<classification>.*?</classification>',res,re.S)
                # assert len(r) == 1 
                # classification_str = r[0]
                # from lxml import etree
                # parser = etree.XMLParser(recover=True)
                # root = etree.fromstring(classification_str, parser=parser)
                # # root = ET.fromstring(classification_str)
                # classifies = root.findall('./classify')
                
                response = []
                statements = [i.strip() for i in re.findall("<statement>(.*?)</statement>",res,re.S)]
                reasons =  [i.strip() for i in  re.findall("<reason>(.*?)</reason>",res,re.S)]
                attributeds = [i.strip() for i in re.findall("<Attributed>(.*?)</Attributed>",res,re.S)]
                
                for statement,reason,attributed in zip(statements,reasons,attributeds):
                    response.append(
                        {
                            "statement": statement,
                            "reason": reason,
                            "Attributed": attributed
                        }
                    )

                
                # for classifie in classifies:
                #     statement = classifie.findall('statement')[0].text.strip()
                #     reason = classifie.findall('reason')[0].text.strip()
                #     attributed = classifie.findall('Attributed')[0].text.strip()
                    # response.append(
                    #     {
                    #         "statement": statement,
                    #         "reason": reason,
                    #         "Attributed": attributed
                    #     }
                    # )

                denom = len(response)
                numerator = sum(
                    item.get("Attributed").lower() == "yes" for item in response
                )
                scores.append(numerator / denom)
            except:
                raise RuntimeError(f'invalid claude generation,prompt:\n{prompt}, \noutput: {res}')

        # scores = []
        # for prompt,res in responses:
        #     try:
        #         response = eval(res)
        #         denom = len(response)
        #         numerator = sum(
        #             item.get("Attributed").lower() == "yes" for item in response
        #         )
        #         scores.append(numerator / denom)
        #     except:
        #         raise RuntimeError(f'invalid claude generation,prompt:\n{prompt}, \noutput: {res}')
            
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