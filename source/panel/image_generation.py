import os
import boto3
import json
import logging
import time
import json

from langchain import PromptTemplate
from langchain.llms.bedrock import Bedrock
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple
from langchain.docstore.document import Document
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS

from dotenv import load_dotenv
# load .env file with specific name
load_dotenv(dotenv_path='.env_sd')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import streamlit as st
import requests
import time

# load the URL from .env file
API_KEY = os.getenv("API_KEY")
# 'https://xxxx.execute-api.us-west-2.amazonaws.com/prod/'
COMMAND_API_URL = os.getenv("COMMON_API_URL")
GENERATE_API_URL = COMMAND_API_URL + "inference-api/inference"
STATUS_API_URL = COMMAND_API_URL + "inference/get-inference-job"
IMAGE_API_URL = COMMAND_API_URL + "inference/get-inference-job-param-output"

def deploy_sagemaker_endpoint():
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'x-api-key': API_KEY
    }
    inputBody = {
        "instance_type": "ml.g4dn.4xlarge",
        "initial_instance_count": "1"
    }    
    # https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/deploy-sagemaker-endpoint
    res = requests.post(COMMAND_API_URL + 'inference/deploy-sagemaker-endpoint', headers = headers, json = inputBody)
    logger.info("deploy_sagemaker_endpoint: {}".format(res.json()))

def get_bedrock_client():
    # specify the profile_name to call the bedrock api if needed
    bedrock_client = boto3.client('bedrock-runtime')
    return bedrock_client

def claude_template(initial_prompt: str, placeholder: str):
    sd_prompt = PromptTemplate(
        input_variables=["initial_prompt", "placeholder"], 
        template="""
    - Transform the input prompt {initial_prompt} into a detailed prompt for an image generation model, describing the scene with vivid and specific attributes that enhance the original concept, only adjective and noun are allowed, verb and adverb are not allowed, each words speperated by comma.
    - Generate a negative prompt that specifies what should be avoided in the image, including any elements that contradict the desired style or tone.
    - Recommend a list of suitable models from the stable diffusion lineup that best match the style and content described in the detailed prompt.
    - Other notes please refer to {placeholder}

    The output should be a plain text in Python List format shown follows, no extra content added beside Positive Prompt, Negative Prompt and Recommended Model List. The model list can only be chosen from the fixed list: "sd_xl_base_1.0.safetensors", "majicmixRealistic_v7.safetensors", "x2AnimeFinal_gzku.safetensors":
    
    [Positive Prompt: <detailed_prompt>,
    Negative Prompt: <negative_prompt>,
    Recommended Model List: <model_list>]
    
    For example:
    If the input prompt is: "a cute dog in cartoon style", the output should be as follows:
    [Positive Prompt: "visually appealing, high-quality image of a cute dog in a vibrant, cartoon style, adorable appearance, expressive eyes, friendly demeanor, colorful and lively, reminiscent of popular animation studios, artwork.",
    Negative Prompt: "realism, dark or dull colors, scary or aggressive dog depictions, overly simplistic, stick figure drawings, blurry or distorted images, inappropriate or NSFW content.",
    Recommended Model List: ["Stable-diffusion: LahCuteCartoonSDXL_alpha.safetensors", "Other model recommended..."]]
    <initial_prompt>
    {initial_prompt}
    </initial_prompt>
    """
    )
    # Pass in values to the input variables
    prompt = sd_prompt.format(initial_prompt="a cute dog", placeholder="")    
    return prompt

def get_llm_processed_prompts(initial_prompt):
    # get the bedrock client
    bedrock_client = get_bedrock_client()

    prompt = claude_template(initial_prompt, '')
    prompt = "\n\nHuman:{}".format(prompt) + "\n\nAssistant:"
    logger.debug("final prompt: {}".format(prompt))    
    body = json.dumps({
        "prompt": prompt,
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 0,
        "max_tokens_to_sample": 500,
        "stop_sequences": ["\n\nHuman:"]
    })
    # note v2 is not output chinese characters
    modelId = "anthropic.claude-v2"
    accept = "*/*"
    contentType = "application/json"
    response = bedrock_client.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    raw_completion = response_body.get("completion").split('\n')
    logger.info("raw_completion: {}".format(raw_completion))

    # TODO: extract positive prompt, negative prompt and model list from the raw_completion

    logger.info("positive_prompt: {}".format(positive_prompt))
    logger.info("negative_prompt: {}".format(negative_prompt))
    logger.info("model_list: {}".format(model_list))
    return positive_prompt, negative_prompt, model_list

def generate_image(positive_prompt, negative_prompt, model: List[str]):
    # Construct the API request (this is a placeholder)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        'x-api-key': API_KEY
    }
    body = {
        "task_type": "txt2img",
        "models": {
            model
        },
        "sagemaker_endpoint_name": '<your endpoint>',
        "prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "denoising_strength": 0.75
    }

    response = requests.post(COMMAND_API_URL + "inference-api/inference", headers = headers, json = body)
    return response.json()

def check_image_status(inference_id: str):
    """Check the status of the image generation."""
    headers = {
        'Accept': 'application/json',
        'x-api-key': API_KEY
    }
    # TODO, the schema is not completed according to the API document
    response = requests.get(GENERATE_API_URL, headers = headers)
    return response.json()

def get_image_url(inference_id):
    """Get the URL of the generated image."""
    response = requests.get(f"{IMAGE_API_URL}/{inference_id}")
    return response.json()

def streamlit():
    # Streamlit layout
    st.title("Image Generation Application")

    # User input
    prompt = st.text_input("Enter a prompt for the image:", "A cute dog")

    # Button to start the image generation process
    if st.button('Generate Image'):
        positive_prompt, negative_prompt, model_list = get_llm_processed_prompts(prompt)
        # Assuming the first model is chosen for simplicity
        # chosen_model = model_list.split('\n')[0]

        # Generate the detailed prompt
        response = generate_image(positive_prompt, negative_prompt, model_list)
        
        # Display image (placeholder for actual image retrieval logic)
        st.image("https://picsum.photos/200", caption=positive_prompt)

        if response.status_code == 200:
            inference_id = response.json()['inference_id']
            # Check the status periodically
            with st.empty():
                while True:
                    status_response = check_image_status(inference_id)
                    if status_response['status'] == 'succeeded':
                        image_url = get_image_url(inference_id)['url']
                        st.image(image_url)
                        break
                    elif status_response['status'] == 'failed':
                        st.error("Image generation failed.")
                        break
                    else:
                        st.text("Waiting for the image to be generated...")
                        time.sleep(5)  # Sleep for a while before checking the status again
        else:
            st.error("Failed to start the image generation process.")

# main entry point for debugging
if __name__ == "__main__":
    # deploy_sagemaker_endpoint()
    # get_llm_processed_prompts("a cute dog")

    # python -m streamlit run image-generation.py --server.port 8088
    streamlit()
