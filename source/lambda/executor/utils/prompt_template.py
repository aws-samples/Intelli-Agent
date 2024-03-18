import re
from typing import List

from langchain.prompts import (
    AIMessagePromptTemplate,
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema.messages import BaseMessage, SystemMessage, _message_from_dict
from langchain.schema.runnable import (
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from .constant import AI_MESSAGE_TYPE, HUMAN_MESSAGE_TYPE, SYSTEM_MESSAGE_TYPE


def convert_text_from_fstring_format(text):
    return text.replace("{", "{{").replace("}", "}}")


def convert_chat_history_from_fstring_format(chat_history: List[BaseMessage]):
    assert isinstance(chat_history, list)
    new_chat_history = []
    for message in chat_history:
        assert isinstance(message, BaseMessage), message
        converted_content = convert_text_from_fstring_format(message.content)
        if message.type == AI_MESSAGE_TYPE:
            message_template = AIMessagePromptTemplate.from_template(converted_content)
        elif message.type == HUMAN_MESSAGE_TYPE:
            message_template = HumanMessagePromptTemplate.from_template(
                converted_content
            )
        elif message.type == SYSTEM_MESSAGE_TYPE:
            message_template = SystemMessagePromptTemplate.from_template(
                converted_content
            )
        else:
            raise ValueError(f"invalid message type: {message.type},{message}")
        new_chat_history.append(message_template)
        # new_chat_history.append(_message_from_dict({
        #     "type": message.type,
        #     "data":{
        #         "content": convert_text_from_fstring_format(message.content),
        #         "additional_kwargs": message.additional_kwargs,
        #         "type": message.type
        #         }
        # }))

    return new_chat_history


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


CLAUDE21_RAG_CONTEXT_TEMPLATE = """<doc index="{index}">
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

CLAUDE2_RAG_CONTEXT_TEMPLATE = """
<item index="{index}">
{content}
</item>
"""


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


############ rag prompt template chain ###############


def get_claude_rag_context(contexts: list):
    assert isinstance(contexts, list), contexts
    context_xmls = []
    context_template = """<doc index="{index}">\n{content}\n</doc>"""
    for i, context in enumerate(contexts):
        context_xml = context_template.format(index=i + 1, content=context)
        context_xmls.append(context_xml)

    context = "\n".join(context_xmls)
    return context


BEDROCK_RAG_CHAT_SYSTEM_PROMPT = """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
<guidelines>
- NERVER say "根据搜索结果/大家好/谢谢...".
</guidelines>

Here are some documents for you to reference for your query:
<docs>
{context}
</docs>"""


def get_claude_chat_rag_prompt(chat_history: List[BaseMessage]):
    chat_history = convert_chat_history_from_fstring_format(chat_history)
    # chat_history = [(ch[0],convert_text_from_fstring_format(ch[1])) for ch in chat_history]
    chat_messages = [
        SystemMessagePromptTemplate.from_template(BEDROCK_RAG_CHAT_SYSTEM_PROMPT)
    ]

    chat_messages = chat_messages + chat_history
    chat_messages += [HumanMessagePromptTemplate.from_template("{query}")]
    context_chain = RunnablePassthrough.assign(
        context=RunnableLambda(
            lambda x: convert_text_from_fstring_format(
                get_claude_rag_context(x["contexts"])
            )
        )
    )

    return context_chain | ChatPromptTemplate.from_messages(chat_messages)


############### chit-chat template #####################
CHIT_CHAT_SYSTEM_TEMPLATE = """You are a helpful AI Assistant"""


def get_chit_chat_prompt(chat_history: List[BaseMessage]):
    chat_history = convert_chat_history_from_fstring_format(chat_history)
    # chat_history = [(ch[0],convert_text_from_fstring_format(ch[1])) for ch in chat_history]
    chat_messages = [
        SystemMessagePromptTemplate.from_template(CHIT_CHAT_SYSTEM_TEMPLATE)
    ]
    chat_messages += chat_history
    chat_messages += [HumanMessagePromptTemplate.from_template("{query}")]
    return ChatPromptTemplate.from_messages(chat_messages)


############### conversation summary template #####################
CQR_SYSTEM_PROMPT = """Given a question and its context, decontextualize the question by addressing coreference and omission issues. The resulting question should retain its original meaning and be as informative as possible, and should not duplicate any previously asked questions in the context.
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


def get_conversation_query_rewrite_prompt(chat_history: List[BaseMessage]):
    conversational_contexts = []
    for his in chat_history:
        assert his.type in [HUMAN_MESSAGE_TYPE, AI_MESSAGE_TYPE]
        if his.type == HUMAN_MESSAGE_TYPE:
            conversational_contexts.append(f"Q: {his.content}")
        else:
            conversational_contexts.append(f"A: {his.content}")

    conversational_context = "\n".join(conversational_contexts)
    conversational_context = convert_text_from_fstring_format(
        f"[{conversational_context}]"
    )

    cqr_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=CQR_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(
                f"\nContext: {conversational_context}\nQuestion: {{query}}\nRewrite: "
            ),
        ]
    )
    return cqr_template


####### hyde prompt ###############

# WEB_SEARCH_TEMPLATE = """Please write a passage to answer the question
# Question: {query}
# Passage:"""
# HYDE_WEB_SEARCH_TEMPLATE = PromptTemplate(template=WEB_SEARCH_TEMPLATE, input_variables=["query"])
