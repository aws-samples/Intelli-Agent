
import re 
from langchain.prompts import PromptTemplate,ChatPromptTemplate
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)


CLAUDE21_RAG_PROMPT_TEMPLTE = """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
<guidelines>
- NERVER say "根据搜索结果/大家好/谢谢...".
</guidelines>

Here are some documents for you to reference for your query:
<docs>
{context}
</docs>

\n\nHuman:The user's query is:
<query>
{query}
</query>

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


# You ALWAYS follow these guidelines when writing your response:
# <guidelines>
# - Only answer with one category and wraper with xml tag <category></category>, NERVER provide any explanation for your answer.
# </guidelines>


INTENT_RECOGINITION_PROMPT_TEMPLATE_CLUADE = """

Human: Please classify this query: <query>{query}</query>. The categories are:

{categories}

Some examples of how to classify queries:
{examples}

Now classify the original query. Respond with just one letter corresponding to the correct category.


Assistant:"""

INTENT_RECOGINITION_EXAMPLE_TEMPLATE = """<query>{query}</query>\n{label}"""


CHAT_PROMPT_TEMPLATE_CLAUDE = """\n\nHuman:{query}
\n\nAssistant:
"""

# def claude2_rag_template_render(
#         query:str,contexts:list,
#         rag_context_template=CLAUDE2_RAG_CONTEXT_TEMPLATE,
#         rag_template = CLAUDE2_RAG_PROMPT_TEMPLTE
#         ):
#     """use claude2 offical rag prompte template

#     Args:
#         query (str): _description_
#         contexts (list): _description_
#     """

#     assert isinstance(contexts,list), contexts
#     context_xmls = []
#     for i,context in enumerate(contexts):
#         context_xml = rag_context_template.format(
#             index = i+1,
#             content = context
#         )
#         context_xmls.append(context_xml)
    
#     context = "\n".join(context_xmls)
#     prompt = rag_template.format(query=query,context=context)
#     return prompt


# def claude21_rag_template_render(
#         query:str,
#         contexts:list,
#         rag_context_template=CLAUDE21_RAG_CONTEXT_TEMPLATE,
#         rag_template = CLAUDE21_RAG_PROMPT_TEMPLTE
#         ):
#     """use claude2 offical rag prompte template

#     Args:
#         query (str): _description_
#         contexts (list): _description_
#     """
#     return claude2_rag_template_render(
#         query,
#         contexts,
#         rag_context_template=rag_context_template,
#         rag_template=rag_template
#         )


# def claude2_rag_api_postprocess(answer):
#     rets = re.findall('<result>(.*?)</result>','<result>'+ answer,re.S)
#     rets = [ret.strip() for ret in rets]
#     rets = [ret for ret in rets if ret]
#     if not rets:
#         return answer  
#     return rets[0]


# def claude_chat_template_render(query:str):
#     return CHAT_PROMPT_TEMPLATE_CLAUDE.format(query=query)

# claude21_rag_api_postprocess = claude2_rag_api_postprocess

# def claude2_rag_stream_postprocess(answer):
#     assert not isinstance(answer,str), answer
#     for answer_chunk in answer:
#         yield answer_chunk.rstrip('</result>')


# claude21_rag_stream_postprocess = claude2_rag_stream_postprocess



############ rag prompt template chain ###############

def get_claude_rag_context(contexts:list):
    assert isinstance(contexts,list), contexts
    context_xmls = []
    context_template = """<doc index="{index}">\n{content}\n</doc>"""
    for i,context in enumerate(contexts):
        context_xml = context_template.format(
            index = i+1,
            content = context
        )
        context_xmls.append(context_xml)
    
    context = "\n".join(context_xmls)
    return context
    

bedrock_rag_chat_system_prompt = """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
<guidelines>
- NERVER say "根据搜索结果/大家好/谢谢...".
</guidelines>

Here are some documents for you to reference for your query:
<docs>
{context}
</docs>"""

def get_claude_chat_rag_prompt(chat_history:list):
    chat_messages = [("system",bedrock_rag_chat_system_prompt)]
    chat_messages = chat_messages + chat_history 
    chat_messages += [("user","{query}")]
    context_chain = RunnablePassthrough.assign(context=RunnableLambda(lambda x:get_claude_rag_context(x['contexts'])))

    return context_chain | ChatPromptTemplate.from_messages(chat_messages)


############### chit-chat template #####################
def get_chit_chat_system_prompt():
    system_prompt = """You are a helpful AI Assistant"""
    return system_prompt

def get_chit_chat_prompt(chat_history:list):
    chat_messages = [("system",get_chit_chat_system_prompt())]
    chat_messages += chat_history 
    chat_messages += [('user',"{query}")]

    return ChatPromptTemplate.from_messages(chat_messages)

cqr_system_prompt = """Given a question and its context, decontextualize the question by addressing coreference and omission issues. The resulting question should retain its original meaning and be as informative as possible, and should not duplicate any previously asked questions in the context.
Context: [Q: When was Born to Fly released?
A: Sara Evans’s third studio album, Born to Fly, was released on October 10, 2000.
]
Question: Was Born to Fly well received by critics?
Rewrite: Was Born to Fly well received by critics?

Context: [Q: When was Keith Carradine born?
A: Keith Ian Carradine was born August 8, 1949.
Q: Is he married?
A: Keith Carradine married Sandra Will on February 6, 1982. ]
Question: Do they have any children?
Rewrite: Do Keith Carradine and Sandra Will have any children?"""
def get_conversation_query_rewrite_prompt(chat_history:list):
    conversational_contexts = []
    for his in chat_history:
        assert his[0] in ['user','ai']
        if his[0] == 'user':
            conversational_contexts.append(f"Q: {his[1]}")
        else:
            conversational_contexts.append(f"A: {his[1]}")
    
    conversational_context = "\n".join(conversational_contexts)
    conversational_context = f'[{conversational_context}]'
    cqr_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    cqr_system_prompt,
                ),
                # New question
                ("user", f"\nContext: {conversational_context}\nQuestion: {{query}}\nRewrite: ")
            ]
            )
    return cqr_template


####### hyde prompt ###############

web_search_template = """Please write a passage to answer the question 
Question: {query}
Passage:"""
hyde_web_search_template = PromptTemplate(template=web_search_template, input_variables=["query"])

    
