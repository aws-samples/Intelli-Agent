import boto3 
import json 
import requests 


class Claude2:
    modelId = 'anthropic.claude-v2'
    accept = 'application/json'
    contentType = 'application/json'
    client = None  
    region_name = 'us-east-1'
    credentials_profile_name = 'default'

    default_generate_kwargs = {
     "max_tokens_to_sample": 2000,
     "temperature": 0.7,
     "top_p": 0.9,
    }

    @classmethod
    def create_client(cls):
        sess = boto3.Session(
            profile_name=cls.credentials_profile_name,
            region_name=cls.region_name
        )
        bedrock = sess.client(
            service_name='bedrock-runtime',
            
            )
        return bedrock

    @classmethod
    def generate(cls,prompt,use_default_prompt_template=True,**generate_kwargs):
        if cls.client is None:
            cls.client = cls.create_client()
  
        generate_kwargs = dict(cls.default_generate_kwargs.copy(),**generate_kwargs)
        if use_default_prompt_template:
            prompt=f"\n\nHuman:{prompt}\n\nAssistant:"
      
        body = json.dumps(dict(generate_kwargs,prompt=prompt))

        response = cls.client.invoke_model(body=body, modelId=cls.modelId, accept=cls.accept, contentType=cls.contentType)

        response_body = json.loads(response.get('body').read())
        # text
        return response_body.get('completion')

    @classmethod
    def batch_generate(cls,prompts,use_default_prompt_template=True,**generate_kwargs):
        assert isinstance(prompts,list)
        ret = []
        for prompt in prompts:
            r = cls.generate(
                prompt,
                use_default_prompt_template = use_default_prompt_template,
                **generate_kwargs
                )
            ret.append(r)
        return ret 
            


class ClaudeInstance(Claude2):
    modelId = 'anthropic.claude-instant-v1'


class Claude21(Claude2):
    modelId = 'anthropic.claude-v2:1'

class CSDCDGRModel:
    @staticmethod
    def generate(
        prompt,
        dgr_url = None,
        **generate_kwargs
        ):
        
        json_data = {
                "model": "knowledge_qa",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                **generate_kwargs
            }
        
        r = requests.post(
            dgr_url,
            json=json_data
            )

        if r.status_code != 200:
            raise RuntimeError(r.json())
        return r.json()