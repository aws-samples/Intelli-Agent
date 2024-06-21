from langchain.pydantic_v1 import BaseModel,Field
from collections import defaultdict

class PromptTemplate(BaseModel):
    model_id: str = Field(description="model_id")
    task_type: str = Field(description="task type")
    prompt_name: str = Field(description="prompt name",default="main")
    prompt_template: str = Field(description="prompt template")


class PromptTemplateManager:
    def __init__(self) -> None:
        self.prompt_templates = defaultdict(dict)

    def get_prompt_template_id(self,model_id,task_type):
        return f"{model_id}__{task_type}"
    
    def register_prompt_template(self,model_id:str,task_type:str,prompt_template:str,prompt_name="main"):
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
            prompt_name="main"
        ):
        assert isinstance(model_ids,list), model_ids
        for model_id in model_ids:
            self.register_prompt_template(
                model_id=model_id,
                task_type=task_type,
                prompt_name=prompt_name,
                prompt_template=prompt_template
            )
    
    def get_prompt_template(self,model_id:str,task_type:str,prompt_name="main"):
        prompt_template_id = self.get_prompt_template_id(model_id,task_type)
        return self.prompt_templates[prompt_template_id][prompt_name]

prompt_template_manager = PromptTemplateManager()
get_prompt_template = prompt_template_manager.get_prompt_template
register_prompt_template = prompt_template_manager.register_prompt_template
register_prompt_templates = prompt_template_manager.register_prompt_templates