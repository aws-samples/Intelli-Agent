
import re 

CLAUDE21_RAG_PROMPT_TEMPLTE = """You are a customer service agent, and answering user's query.
Here are some documents for you to reference for your query:
<docs>
{context}
</docs>

\n\nHuman:The user's query is:
<query>
{query}
</query>

NERVER say "根据搜索结果...".

Provide a response between <result> tags.
\n\nAssistant:<result> 
"""


CLAUDE21_RAG_CONTEXT_TEMPLATE="""<doc index="{index}">
{content}
</doc>
"""

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


INTENT_RECOGINITION_PROMPT_TEMPLATE_CLUADE21 = """\n\nHuman: You are a customer service agent that is classifying user's query wrapped by <query></query>.
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


CHAT_PROMPT_TEMPLATE_CLAUDE = """\n\nHuman:{query}
\n\nAssistant:
"""


def claude2_rag_template_render(
        query:str,contexts:list,
        rag_context_template=CLAUDE2_RAG_CONTEXT_TEMPLATE,
        rag_template = CLAUDE2_RAG_PROMPT_TEMPLTE
        ):
    """use claude2 offical rag prompte template

    Args:
        query (str): _description_
        contexts (list): _description_
    """

    assert isinstance(contexts,list), contexts
    context_xmls = []
    for i,context in enumerate(contexts):
        context_xml = rag_context_template.format(
            index = i+1,
            content = context
        )
        context_xmls.append(context_xml)
    
    context = "\n".join(context_xmls)
    prompt = rag_template.format(query=query,context=context)
    return prompt



def claude21_rag_template_render(
        query:str,
        contexts:list,
        rag_context_template=CLAUDE21_RAG_CONTEXT_TEMPLATE,
        rag_template = CLAUDE21_RAG_PROMPT_TEMPLTE
        ):
    """use claude2 offical rag prompte template

    Args:
        query (str): _description_
        contexts (list): _description_
    """
    return claude2_rag_template_render(
        query,
        contexts,
        rag_context_template=rag_context_template,
        rag_template=rag_template
        )


def claude2_rag_api_postprocess(answer):
    rets = re.findall('<result>(.*?)</result>','<result>'+ answer,re.S)
    rets = [ret.strip() for ret in rets]
    rets = [ret for ret in rets if ret]
    if not rets:
        return answer  
    return rets[0]


def claude_chat_template_render(query:str):
    return CHAT_PROMPT_TEMPLATE_CLAUDE.format(query=query)

claude21_rag_api_postprocess = claude2_rag_api_postprocess

def claude2_rag_stream_postprocess(answer):
    assert not isinstance(answer,str), answer
    for answer_chunk in answer:
        yield answer_chunk.rstrip('</result>')


claude21_rag_stream_postprocess = claude2_rag_stream_postprocess


