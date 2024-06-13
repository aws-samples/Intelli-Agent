from langchain.prompts import PromptTemplate
from langchain.llms import SagemakerEndpoint
from typing import Any, Dict, List, Union,Mapping, Optional, TypeVar, Union
from langchain.chains import LLMChain
from langchain.llms.bedrock import Bedrock
from botocore.exceptions import ClientError
import boto3
import os

BEDROCK_REGION = os.environ.get('region','us-west-2')
def service_org(**args):
    context = """placeholder"""
    
    prompt_tmp = """
        你是云服务AWS的智能客服机器人AWSBot

        给你 SSO (Service Specialist Organization) 的组织信息
        {context}

        Job role (角色, 岗位类型) description:
        - GTMS: Go To Market Specialist
        - SS: Specialist Sales
        - SSA: Specialist Solution Architechure
        - TPM: 
        - PM: Project Manager

        Scope means job scope
        service_name equal to business unit

        If the context does not contain the knowleage for the question, truthfully says you does not know.
        Don't put two people's names together. For example, zheng zhang not equal to zheng hao and xueqing not equal to Xueqing Lai

        Find out the most relevant context, and give the answer according to the context
        Skip the preamble; go straight to the point.
        Only give the final answer.
        Do not repeat similar answer.
        使用中文回复，人名不需要按照中文习惯回复

        {question}
        """

    def create_prompt_templete(prompt_template):
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context",'question','chat_history']
        )
        return PROMPT


    boto3_bedrock = boto3.client(
            service_name="bedrock-runtime",
            region_name=BEDROCK_REGION
        )
    
    parameters = {
        "max_tokens_to_sample": 8096,
        "stop_sequences": ["\nObservation"],
        "temperature":0.01,
        "top_p":0.85
    }
        
    model_id = "anthropic.claude-v2"
    llm = Bedrock(model_id=model_id, client=boto3_bedrock, model_kwargs=parameters)
    
    prompt = create_prompt_templete(prompt_tmp) 
    llmchain = LLMChain(llm=llm,verbose=False,prompt = prompt)
    answer = llmchain.run({'question':args.get('query'), "context": context})
    answer = answer.strip()
    return answer

def lambda_handler(event, context=None):
    '''
    event: {
        \"query\":\"Bruce负责哪一块？\"
    }
    '''
    result = service_org(**event)
    return {"code":0, "result": result}

if __name__ == "__main__":
    args = {'query': 'Bruce负责哪一块？'}
    print(service_org(**args))