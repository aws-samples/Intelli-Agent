
import re 

CLAUDE2_RAG_PROMPT_TEMPLTE = """\n\nHuman:
Here is a query:

<query>
{query}
</query>

Here are some results relevant to the query:

<search_results>
{context}
</search results>

Once again, the user's query is:

<query>
{query}
</query>

Provide a response between <result> tags.
\n\nAssistant:<result> 
"""

CLAUDE2_RAG_CONTEXT_TEMPLATE="""
<item index="{index}">
{content}
</item>
"""


INTENT_RECOGINITION_PROMPT_TEMPLATE = """\n\nHuman: You are a customer service agent that is classifying user's query wrapped by <query></query>.
The all categories and their few-shot examples are shown below.

{few_shot_examples}

Categories are:
{all_labels}

User's query:
<query>
{query}
</query>

\n\nAssistant: My answer is <category>
"""

INTENT_RECOGINITION_EXAMPLE_TEMPLATE = """<example>\n<query>{query}</query>\n<category>{label}</category>\n</example>"""



def claude2_rag_template_render(query:str,contexts:list):
    """use claude2 offical rag prompte template

    Args:
        query (str): _description_
        contexts (list): _description_
    """
    assert isinstance(contexts,list), contexts
    context_xmls = []
    for i,context in enumerate(contexts):
        context_xml = CLAUDE2_RAG_CONTEXT_TEMPLATE.format(
            index = i+1,
            content = context
        )
        context_xmls.append(context_xml)
    
    context = "\n".join(context_xmls)
    prompt = CLAUDE2_RAG_PROMPT_TEMPLTE.format(query=query,context=context)
    return prompt

def claude2_rag_api_postprocess(answer):
    rets = re.findall('<result>(.*?)</result>','<result>'+ answer,re.S)
    rets = [ret.strip() for ret in rets]
    rets = [ret for ret in rets if ret]
    if not rets:
        return answer  
    return rets[0]

def claude2_rag_stream_postprocess(answer):
    assert not isinstance(answer,str), answer
    for answer_chunk in answer:
        yield answer_chunk.rstrip('</result>')


