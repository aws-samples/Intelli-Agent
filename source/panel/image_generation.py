import os
import boto3
import json
import logging
import time
import json

from langchain.prompts import PromptTemplate
from langchain.llms.bedrock import Bedrock
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple
from langchain.docstore.document import Document
from langchain.chains import ConversationChain
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory

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

def deploy_sagemaker_endpoint(instance_type: str = "ml.g4dn.4xlarge", initial_instance_count: int = 1, endpoint_name: str = "default-endpoint-for-llm-bot"):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': API_KEY
    }
    inputBody = {
        "instance_type": instance_type,
        "initial_instance_count": initial_instance_count,
        "endpoint_name": endpoint_name
    }    
    # https://<Your API Gateway ID>.execute-api.<Your AWS Account Region>.amazonaws.com/{basePath}/inference/deploy-sagemaker-endpoint
    res = requests.post(COMMAND_API_URL + 'inference/deploy-sagemaker-endpoint', headers = headers, json = inputBody)
    logger.info("deploy_sagemaker_endpoint: {}".format(res.json()))

def upload_model():
    pass

def get_bedrock_llm():
    # specify the profile_name to call the bedrock api if needed
    bedrock_client = boto3.client('bedrock-runtime')

    modelId = "anthropic.claude-v2"
    cl_llm = Bedrock(
        model_id=modelId,
        client=bedrock_client,
        model_kwargs={"max_tokens_to_sample": 1000},
    )
    return cl_llm

sd_prompt = PromptTemplate.from_template(
    """
    Human:
    - Transform the input prompt {input} into a detailed prompt for an image generation model, describing the scene with vivid and specific attributes that enhance the original concept, only adjective and noun are allowed, verb and adverb are not allowed, each words speperated by comma.
    - Generate a negative prompt that specifies what should be avoided in the image, including any elements that contradict the desired style or tone.
    - Recommend a list of suitable models from the stable diffusion lineup that best match the style and content described in the detailed prompt.
    - Other notes please refer to the following example:

    The output should be a plain text in Python List format shown follows, no extra content added beside Positive Prompt, Negative Prompt and Recommended Model List. The model list can only be chosen from the fixed list: "sd_xl_base_1.0.safetensors", "majicmixRealistic_v7.safetensors", "x2AnimeFinal_gzku.safetensors":
    
    [Positive Prompt: <detailed_prompt>,
    Negative Prompt: <negative_prompt>,
    Recommended Model List: <model_list>]
    
    For example:
    If the input prompt is: "a cute dog in cartoon style", the output should be as follows:
    [Positive Prompt: "visually appealing, high-quality image of a cute dog in a vibrant, cartoon style, adorable appearance, expressive eyes, friendly demeanor, colorful and lively, reminiscent of popular animation studios, artwork.",
    Negative Prompt: "realism, dark or dull colors, scary or aggressive dog depictions, overly simplistic, stick figure drawings, blurry or distorted images, inappropriate or NSFW content.",
    Recommended Model List: ["Stable-diffusion: LahCuteCartoonSDXL_alpha.safetensors", "Other model recommended..."]]

    Current conversation:
    <conversation_history>
    {history}
    </conversation_history>

    Here is the human's next reply:
    <human_reply>
    {input}
    </human_reply>

    Assistant:
    """)

def get_llm_processed_prompts(initial_prompt):
    cl_llm = get_bedrock_llm()
    memory = ConversationBufferMemory()
    conversation = ConversationChain(
        llm=cl_llm, verbose=False, memory=memory
    )
 
    conversation.prompt = sd_prompt
    response = conversation.predict(input=initial_prompt)
    logger.info("the first invoke: {}".format(response))
    # logger.info("the second invoke: {}".format(conversation.predict(input="change to realist style")))

    """
    [Positive Prompt: visually appealing, high-quality image of a big, large, muscular horse with powerful body, majestic stance, flowing mane, detailed texture, vivid color, striking photography.,
    Negative Prompt: ugly, distorted, inappropriate or NSFW content,
    Recommended Model List: ["sd_xl_base_1.0.safetensors"]]
    """
    positive_prompt = response.split('Positive Prompt: ')[1].split('Negative Prompt: ')[0].strip()
    negative_prompt = response.split('Negative Prompt: ')[1].split('Recommended Model List: ')[0].strip()
    model_list = response.split('Recommended Model List: ')[1].strip().replace('[', '').replace(']', '').replace('"', '').split(',')
    logger.info("positive_prompt: {}\n negative_prompt: {}\n model_list: {}".format(positive_prompt, negative_prompt, model_list))
    return positive_prompt, negative_prompt, model_list

def generate_image(endpoint_name: str, positive_prompt: str, negative_prompt: str, model: List[str]):
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
        "sagemaker_endpoint_name": endpoint_name,
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
    # upload_model()
    positive_prompt, negative_prompt, model_list = get_llm_processed_prompts("a big horse")
    # The endpoint fixed for now, since the deploy_sagemaker_endpoint() won't return the endpoint name
    # response = generate_image("default-endpoint-for-llm-bot", positive_prompt, negative_prompt, model_list)
    # logger.info("generate image response: {}".format(response))

    # python -m streamlit run image-generation.py --server.port 8088
    # streamlit()
