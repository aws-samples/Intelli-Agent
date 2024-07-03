import boto3
import os

from langchain.pydantic_v1 import BaseModel,Field
from collections import defaultdict
from common_logic.common_utils.constant import LLMModelType,LLMTaskType
import copy

ddb_prompt_table_name = os.environ.get("prompt_table_name", "")
dynamodb_resource = boto3.resource("dynamodb")
ddb_prompt_table = dynamodb_resource.Table(ddb_prompt_table_name)



# export models to front
EXPORT_MODEL_IDS = [
    LLMModelType.CLAUDE_3_HAIKU,
    LLMModelType.CLAUDE_3_SONNET,
    LLMModelType.CLAUDE_2,
    LLMModelType.CLAUDE_21
]

class PromptTemplate(BaseModel):
    model_id: str = Field(description="model_id")
    task_type: str = Field(description="task type")
    prompt_name: str = Field(description="prompt name",default="system_prompt")
    prompt_template: str = Field(description="prompt template")


class PromptTemplateManager:
    def __init__(self) -> None:
        self.prompt_templates = defaultdict(dict)

    def get_prompt_template_id(self,model_id,task_type):
        return f"{model_id}__{task_type}"
    
    def register_prompt_template(self,model_id:str,task_type:str,prompt_template:str,prompt_name="system_prompt"):
        assert model_id and task_type and prompt_name, (model_id,task_type,prompt_name)
        prompt_template = PromptTemplate(
            model_id=model_id,
            task_type=task_type,
            prompt_template=prompt_template,
            prompt_name=prompt_name
        )
        prompt_template_id = self.get_prompt_template_id(model_id,task_type)
        self.prompt_templates[prompt_template_id][prompt_name] = prompt_template
        
    def register_prompt_templates(
            self,
            model_ids:list,
            task_type:str,
            prompt_template:str,
            prompt_name="system_prompt"
        ):
        assert isinstance(model_ids,list), model_ids
        for model_id in model_ids:
            self.register_prompt_template(
                model_id=model_id,
                task_type=task_type,
                prompt_name=prompt_name,
                prompt_template=prompt_template
            )
    
    def get_prompt_template(self,model_id:str,task_type:str,prompt_name="system_prompt"):
        prompt_template_id = self.get_prompt_template_id(model_id,task_type)
        try:
            return self.prompt_templates[prompt_template_id][prompt_name]
        except KeyError:
            raise KeyError(f'prompt_template_id: {prompt_template_id}, prompt_name: {prompt_name}')

    
    def get_prompt_templates_from_ddb(self,user_id,model_id:str,task_type:str):
        response = ddb_prompt_table.get_item(
            Key={"userId": user_id, "sortKey": f"{model_id}__{task_type}"}
        )
        item = response.get("Item")
        if item:
            return item.get("prompt")
        return {}

    def get_all_templates(self,allow_model_ids=EXPORT_MODEL_IDS):
        assert isinstance(allow_model_ids,list),allow_model_ids
        prompt_templates = copy.deepcopy(self.prompt_templates)
        all_prompt_templates = []
        allow_model_ids = set(allow_model_ids)
        for _,v in prompt_templates.items():
            for _, prompt in v.items():
                if prompt.model_id in allow_model_ids:
                    all_prompt_templates.append(prompt)
                # v[prompt_name] = v[prompt_name].prompt_template
        
        ret = {}
        for prompt_template in all_prompt_templates:
            model_id = prompt_template.model_id
            task_type = prompt_template.task_type
            prompt_name = prompt_template.prompt_name
            prompt_template = prompt_template.prompt_template
            if model_id not in ret:
                ret[model_id] = {"common":{}}
            if task_type not in ret[model_id]["common"]:
                ret[model_id]["common"][task_type] = {}
            
            ret[model_id]["common"][task_type][prompt_name] = prompt_template

        return ret

    
    def prompt_template_render(self,prompt_template:dict):
        pass 



prompt_template_manager = PromptTemplateManager()
get_prompt_template = prompt_template_manager.get_prompt_template
register_prompt_template = prompt_template_manager.register_prompt_template
register_prompt_templates = prompt_template_manager.register_prompt_templates
get_all_templates = prompt_template_manager.get_all_templates
get_prompt_templates_from_ddb = prompt_template_manager.get_prompt_templates_from_ddb


#### rag template #######

CLAUDE_RAG_SYSTEM_PROMPT = """You are a customer service agent, and answering user's query. You ALWAYS follow these guidelines when writing your response:
<guidelines>
- NERVER say "根据搜索结果/大家好/谢谢...".
</guidelines>

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
        LLMModelType.CLAUDE_INSTANCE,
        LLMModelType.MIXTRAL_8X7B_INSTRUCT
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



CHIT_CHAT_SYSTEM_TEMPLATE = "You are a helpful assistant."

register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_INSTANCE,
        LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        LLMModelType.GLM_4_9B_CHAT,
        LLMModelType.QWEN2INSTRUCT72B,
        LLMModelType.QWEN2INSTRUCT7B
    ],
    task_type=LLMTaskType.CHAT,
    prompt_template=CHIT_CHAT_SYSTEM_TEMPLATE,
    prompt_name="system_prompt"
)



CQR_TEMPLATE = """Given the following conversation between `USER` and `AI`, and a follow up `USER` reply, Put yourself in the shoes of `USER`, rephrase the follow up \
`USER` reply to be a standalone reply.

Chat History:
{history}

The USER's follow up reply: {question}"""

register_prompt_templates(
    model_ids=[
        LLMModelType.CLAUDE_2,
        LLMModelType.CLAUDE_21,
        LLMModelType.CLAUDE_3_HAIKU,
        LLMModelType.CLAUDE_3_SONNET,
        LLMModelType.CLAUDE_INSTANCE,
        LLMModelType.MIXTRAL_8X7B_INSTRUCT,
        LLMModelType.QWEN2INSTRUCT72B,
        LLMModelType.QWEN2INSTRUCT7B,
        LLMModelType.GLM_4_9B_CHAT
    ],
    task_type=LLMTaskType.CONVERSATION_SUMMARY_TYPE,
    prompt_template=CQR_TEMPLATE,
    prompt_name="system_prompt"
)



if __name__ == "__main__":
    print(get_all_templates())

