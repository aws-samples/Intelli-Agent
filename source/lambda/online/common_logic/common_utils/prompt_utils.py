import boto3
import os
import json

from langchain.pydantic_v1 import BaseModel, Field
from collections import defaultdict
from common_logic.common_utils.constant import LLMModelType, LLMTaskType
import copy
from common_logic.common_utils.constant import SceneType, MessageType

ddb_prompt_table_name = os.environ.get("PROMPT_TABLE_NAME", "")
dynamodb_resource = boto3.resource("dynamodb")
ddb_prompt_table = dynamodb_resource.Table(ddb_prompt_table_name)


# export models to front
EXPORT_MODEL_IDS = [
    LLMModelType.CLAUDE_3_HAIKU,
    LLMModelType.CLAUDE_3_SONNET,
    LLMModelType.LLAMA3_1_70B_INSTRUCT,
    LLMModelType.MISTRAL_LARGE_2407,
    LLMModelType.COHERE_COMMAND_R_PLUS
]

EXPORT_SCENES = [
    SceneType.COMMON
]


class PromptTemplate(BaseModel):
    model_id: str = Field(description="model_id")
    task_type: str = Field(description="task type")
    prompt_name: str = Field(description="prompt name",
                             default="system_prompt")
    prompt_template: str = Field(description="prompt template")


class PromptTemplateManager:
    def __init__(self) -> None:
        self.prompt_templates = defaultdict(dict)

    def get_prompt_template_id(self, model_id, task_type):
        return f"{model_id}__{task_type}"

    def register_prompt_template(self, model_id: str, task_type: str, prompt_template: str, prompt_name="system_prompt"):
        assert model_id and task_type and prompt_name, (
            model_id, task_type, prompt_name)
        prompt_template = PromptTemplate(
            model_id=model_id,
            task_type=task_type,
            prompt_template=prompt_template,
            prompt_name=prompt_name
        )
        prompt_template_id = self.get_prompt_template_id(model_id, task_type)
        self.prompt_templates[prompt_template_id][prompt_name] = prompt_template

    def register_prompt_templates(
        self,
        model_ids: list,
        task_type: str,
        prompt_template: str,
        prompt_name="system_prompt"
    ):
        assert isinstance(model_ids, list), model_ids
        for model_id in model_ids:
            self.register_prompt_template(
                model_id=model_id,
                task_type=task_type,
                prompt_name=prompt_name,
                prompt_template=prompt_template
            )

    def get_prompt_template(self, model_id: str, task_type: str, prompt_name="system_prompt"):
        prompt_template_id = self.get_prompt_template_id(model_id, task_type)
        try:
            return self.prompt_templates[prompt_template_id][prompt_name]
        except KeyError:
            raise KeyError(
                f'prompt_template_id: {prompt_template_id}, prompt_name: {prompt_name}')

    def get_prompt_templates_from_ddb(self, group_name: str, model_id: str, task_type: str, chatbot_id: str = "admin", scene: str = "common"):
        response = ddb_prompt_table.get_item(
            Key={"GroupName": group_name,
                 "SortKey": f"{model_id}__{scene}__{chatbot_id}"}
        )
        return response.get("Item", {}).get("Prompt", {}).get(task_type, {})

    def get_all_templates(self, allow_model_ids=EXPORT_MODEL_IDS):
        assert isinstance(allow_model_ids, list), allow_model_ids
        prompt_templates = copy.deepcopy(self.prompt_templates)
        all_prompt_templates = []
        allow_model_ids = set(allow_model_ids)
        for _, v in prompt_templates.items():
            for _, prompt in v.items():
                if prompt.model_id in allow_model_ids:
                    all_prompt_templates.append(prompt)

        ret = {}
        for prompt_template in all_prompt_templates:
            model_id = prompt_template.model_id
            task_type = prompt_template.task_type
            prompt_name = prompt_template.prompt_name
            prompt_template = prompt_template.prompt_template
            if model_id not in ret:
                ret[model_id] = {"common": {}}
            if task_type not in ret[model_id]["common"]:
                ret[model_id]["common"][task_type] = {}

            ret[model_id]["common"][task_type][prompt_name] = prompt_template

        return ret

    def prompt_template_render(self, prompt_template: dict):
        pass


prompt_template_manager = PromptTemplateManager()
get_prompt_template = prompt_template_manager.get_prompt_template
register_prompt_template = prompt_template_manager.register_prompt_template
register_prompt_templates = prompt_template_manager.register_prompt_templates
get_all_templates = prompt_template_manager.get_all_templates
get_prompt_templates_from_ddb = prompt_template_manager.get_prompt_templates_from_ddb


#### rag template #######

CLAUDE_RAG_SYSTEM_PROMPT = """You are a customer service agent, and answering user's query. You ALWAYS follow these response rules when writing your response:
<response_rules>
- NERVER say "根据搜索结果/大家好/谢谢/根据这个文档...".
- 回答简单明了
- 如果问题与<docs> </docs>里面的内容不相关，直接回答 "根据内部知识库，找不到相关内容。"
</response_rules>

Here are some documents for you to reference for your query.
<docs>
{context}
</docs>"""

register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
        LLMModelType.CLAUDE_INSTANCE,
        LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        LLMModelType.LLAMA3_1_70B_INSTRUCT,
        LLMModelType.MISTRAL_LARGE_2407,
        LLMModelType.COHERE_COMMAND_R_PLUS,
    ],
    task_type=LLMTaskType.RAG,
    prompt_template=CLAUDE_RAG_SYSTEM_PROMPT,
    prompt_name="system_prompt"
)


GLM4_RAG_SYSTEM_PROMPT = """你是一个人工智能助手，正在回答人类的各种问题，下面是相关背景知识供参考:
# 背景知识
{context}

# 回答规范:
 - 简洁明了，言简意赅。
"""


register_prompt_templates(
    model_ids=[
        LLMModelType.QWEN2INSTRUCT72B,
        LLMModelType.QWEN2INSTRUCT7B,
        LLMModelType.GLM_4_9B_CHAT
    ],
    task_type=LLMTaskType.RAG,
    prompt_template=CLAUDE_RAG_SYSTEM_PROMPT,
    prompt_name="system_prompt"
)


################ 
# query rewrite prompt template from paper https://arxiv.org/pdf/2401.10225
###################
CQR_SYSTEM_PROMPT = """You are a helpful, pattern-following assistant."""

CQR_USER_PROMPT_TEMPLATE = """Given the following conversation between PersonU and PersonA:
{conversation}
Instead of having this entire conversation, how can PersonU get what he or she is
looking for using a single sentence? Keep the recent sentence of PersonU: “{current_query}” to be same if it is already self-explanatory. Don't make any explanations."""


CQR_FEW_SHOTS = [
    {
        "conversation": [
            {
                "role": MessageType.HUMAN_MESSAGE_TYPE,
                "content": "Hello, I would like to know what to do if I do not agree with any decision."
            },
            {
                "role": MessageType.AI_MESSAGE_TYPE,
                "content": "disagree with our decision about your monthly income adjustment amounts?"
            },
            {
                "role": MessageType.HUMAN_MESSAGE_TYPE,
                "content": "no. Where can I find my SHIP contact information?"
            },
            {
                "role": MessageType.AI_MESSAGE_TYPE,
                "content": "You can find your local SHIP contact information in the back of your Medicare & You 2020 Handbook online."
            },
            {
                "role": MessageType.HUMAN_MESSAGE_TYPE,
                "content": "and how do they calculate the adjustments?"
            }
        ],
        "rewrite_query": "How is the calculation for adjustments made by SHIP determined?"
    },
    {
        "conversation": [
            {
                "role": MessageType.HUMAN_MESSAGE_TYPE,
                "content": "I need to know how to prepare for college."
            },
            {
                "role": MessageType.AI_MESSAGE_TYPE,
                "content": "You should first define your goals and interest and be sure to know the costs and how to plan financially and academically for college."
            },
            {
                "role": MessageType.HUMAN_MESSAGE_TYPE,
                "content": "Is there something I can use as a guide to get ready for it?"
            }
        ],
        "rewrite_query": "What resources or guides can I use to help me prepare for college?"
    },
    {
        "conversation": [
            {
                "role": MessageType.HUMAN_MESSAGE_TYPE,
                "content": "垃圾"
            }
        ],
        "rewrite_query": "垃圾"
    },
    {
        "conversation": [
            {
                "role": MessageType.HUMAN_MESSAGE_TYPE,
                "content": "你好"
            }
        ],
        "rewrite_query": "你好"
    },
]

register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
        LLMModelType.CLAUDE_INSTANCE,
        LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        LLMModelType.QWEN2INSTRUCT72B,
        LLMModelType.QWEN2INSTRUCT7B,
        LLMModelType.GLM_4_9B_CHAT,
        LLMModelType.LLAMA3_1_70B_INSTRUCT,
        LLMModelType.MISTRAL_LARGE_2407,
        LLMModelType.COHERE_COMMAND_R_PLUS,
    
    ],
    task_type=LLMTaskType.CONVERSATION_SUMMARY_TYPE,
    prompt_template=CQR_SYSTEM_PROMPT,
    prompt_name="system_prompt"
)

register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
        LLMModelType.CLAUDE_INSTANCE,
        LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        LLMModelType.QWEN2INSTRUCT72B,
        LLMModelType.QWEN2INSTRUCT7B,
        LLMModelType.GLM_4_9B_CHAT,
        LLMModelType.LLAMA3_1_70B_INSTRUCT,
        LLMModelType.MISTRAL_LARGE_2407,
        LLMModelType.COHERE_COMMAND_R_PLUS,
    ],
    task_type=LLMTaskType.CONVERSATION_SUMMARY_TYPE,
    prompt_template=CQR_USER_PROMPT_TEMPLATE,
    prompt_name="user_prompt"
)


register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
        LLMModelType.CLAUDE_INSTANCE,
        LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        LLMModelType.QWEN2INSTRUCT72B,
        LLMModelType.QWEN2INSTRUCT7B,
        LLMModelType.GLM_4_9B_CHAT,
        LLMModelType.LLAMA3_1_70B_INSTRUCT,
        LLMModelType.MISTRAL_LARGE_2407,
        LLMModelType.COHERE_COMMAND_R_PLUS,
    ],
    task_type=LLMTaskType.CONVERSATION_SUMMARY_TYPE,
    prompt_template=json.dumps(CQR_FEW_SHOTS, ensure_ascii=False, indent=2),
    prompt_name="few_shots"
)



############## xml agent prompt #############
AGENT_USER_PROMPT = "你是一个AI助理。今天是{date},{weekday}. "
register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
    ],
    task_type=LLMTaskType.TOOL_CALLING_XML,
    prompt_template=AGENT_USER_PROMPT,
    prompt_name="user_prompt"
)

AGENT_GUIDELINES_PROMPT = """<guidlines>
- Don't forget to output <function_calls> </function_calls> when any tool is called.
- 每次回答总是先进行思考，并将思考过程写在<thinking>标签中。请你按照下面的步骤进行思考:
    1. 判断根据当前的上下文是否足够回答用户的问题。
    2. 如果当前的上下文足够回答用户的问题，请调用 `give_final_response` 工具。
    3. 如果当前的上下文不能支持回答用户的问题，你可以考虑调用<tools> 标签中列举的工具。
    4. 如果调用工具对应的参数不够，请调用反问工具 `give_rhetorical_question` 来让用户提供更加充分的信息。如果调用工具不需要参数，则不需要调用反问工具。
    5. 最后给出你要调用的工具名称。
- Always output with the same language as the content within <query></query>. If the content is english, use englisth to output. If the content is chinese, use chinese to output.
</guidlines>
"""

register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
        LLMModelType.LLAMA3_1_70B_INSTRUCT,
        LLMModelType.MISTRAL_LARGE_2407,
        LLMModelType.COHERE_COMMAND_R_PLUS,
    ],
    task_type=LLMTaskType.TOOL_CALLING_XML,
    prompt_template=AGENT_GUIDELINES_PROMPT,
    prompt_name="guidelines_prompt"
)

################# api agent prompt #####################
AGENT_USER_PROMPT = "你是一个AI助理。今天是{date},{weekday}. "
register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
        LLMModelType.LLAMA3_1_70B_INSTRUCT,
        LLMModelType.MISTRAL_LARGE_2407,
        LLMModelType.COHERE_COMMAND_R_PLUS,
    ],
    task_type=LLMTaskType.TOOL_CALLING_API,
    prompt_template=AGENT_USER_PROMPT,
    prompt_name="user_prompt"
)

AGENT_GUIDELINES_PROMPT = """<guidlines>
- 每次回答总是先进行思考，并将思考过程写在<thinking>标签中。请你按照下面的步骤进行思考:
    1. 判断根据当前的上下文是否足够回答用户的问题。
    2. 如果当前的上下文足够回答用户的问题，请调用 `give_final_response` 工具。
    3. 如果当前的上下文不能支持回答用户的问题，你可以考虑调用提供的工具。
    4. 如果调用工具对应的参数不够，请调用反问工具 `give_rhetorical_question` 来让用户提供更加充分的信息。如果调用工具不需要参数，则不需要调用反问工具。
    5. 最后给出你要调用的工具名称。
- Always output with the same language as user's query. If the content is english, use englisth to output. If the content is Chinese, use Chinese to output.
</guidlines>
"""

register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_3_5_SONNET,
        LLMModelType.LLAMA3_1_70B_INSTRUCT,
        LLMModelType.MISTRAL_LARGE_2407,
        LLMModelType.COHERE_COMMAND_R_PLUS,
    ],
    task_type=LLMTaskType.TOOL_CALLING_API,
    prompt_template=AGENT_GUIDELINES_PROMPT,
    prompt_name="guidelines_prompt"
)



if __name__ == "__main__":
    print(get_all_templates())
