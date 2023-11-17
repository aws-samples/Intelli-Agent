import json
import logging
import os
import time
from datetime import datetime
from typing import List

import boto3
import requests
import streamlit as st
from dotenv import load_dotenv
from langchain import PromptTemplate
from langchain.chains import ConversationChain
from langchain.llms.bedrock import Bedrock
from langchain.memory import ConversationBufferMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# load .env file with specific name
load_dotenv(dotenv_path='.env_sd')

# Your ApiGatewayUrl in Extension for Stable Diffusion
# Example: https://xxxx.execute-api.us-west-2.amazonaws.com/prod/
COMMAND_API_URL = os.getenv("COMMON_API_URL")
# Your ApiGatewayUrlToken in Extension for Stable Diffusion
API_KEY = os.getenv("API_KEY")
# Your username in Extension for Stable Diffusion
# Some resources are limited to specific users
API_USERNAME = os.getenv("API_USERNAME")
# The service support varies in different regions
BEDROCK_REGION = os.getenv("BEDROCK_REGION")

# API URL
GENERATE_API_URL = COMMAND_API_URL + "inference/v2"
STATUS_API_URL = COMMAND_API_URL + "inference/get-inference-job"
PARAM_API_URL = COMMAND_API_URL + "inference/get-inference-job-param-output"
IMAGE_API_URL = COMMAND_API_URL + "inference/get-inference-job-image-output"
CHECKPOINTS_API_URL = COMMAND_API_URL + "checkpoints"

support_model_list = []
default_models = ["v1-5-pruned-emaonly.safetensors"]

# todo will update api
def deploy_sagemaker_endpoint(instance_type: str = "ml.g4dn.4xlarge", initial_instance_count: int = 1,
                              endpoint_name: str = "default-endpoint-for-llm-bot"):
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
    bedrock_client = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)

    modelId = "anthropic.claude-v2"
    cl_llm = Bedrock(
        model_id=modelId,
        client=bedrock_client,
        model_kwargs={"max_tokens_to_sample": 1000},
    )
    return cl_llm

# todo template use dynamic checkpoints
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

    positive_prompt = response.split('Positive Prompt: ')[1].split('Negative Prompt: ')[0].strip()
    negative_prompt = response.split('Negative Prompt: ')[1].split('Recommended Model List: ')[0].strip()
    model_list = response.split('Recommended Model List: ')[1].strip().replace('[', '').replace(']', '').replace('"', '').split(',')
    logger.info("positive_prompt: {}\n negative_prompt: {}\n model_list: {}".format(positive_prompt, negative_prompt, model_list))
    return positive_prompt, negative_prompt, model_list


def generate_image(positive_prompts: str, negative_prompts: str, model: List[str], current_col, progress_bar):

    job = create_inference_job(model)
    st.session_state.progress += 5
    progress_bar.progress(st.session_state.progress)

    inference = job["inference"]

    upload_inference_job_api_params(inference["api_params_s3_upload_url"], positive_prompts, negative_prompts)
    st.session_state.progress += 5
    progress_bar.progress(st.session_state.progress)

    run_inference_job(inference["id"])
    st.session_state.progress += 5
    progress_bar.progress(st.session_state.progress)

    while True:
        status_response = get_inference_job(inference["id"])
        if st.session_state.progress < 80:
            st.session_state.progress += 10
        progress_bar.progress(st.session_state.progress)
        if status_response['status'] == 'succeed':
            progress_bar.progress(100)
            image_url = get_inference_image_output(inference["id"])[0]
            current_col.image(image_url, use_column_width=True)
            break
        elif status_response['status'] == 'failed':
            current_col.error("Image generation failed.")
            break
        else:
            time.sleep(1)

    for item in st.session_state.warning:
        current_col.warning(item)

    api_params = get_inference_param_output(inference["id"])
    params = requests.get(api_params[0]).json()
    info = json.loads(params['info'])

    if info["prompt"] != "":
        current_col.write("prompt:")
        current_col.info(info["prompt"])

    if info["negative_prompt"] != "":
        current_col.write("negative_prompt:")
        current_col.info(info["negative_prompt"])

    if info["sd_model_name"] != "":
        current_col.write("sd_model_name:")
        current_col.info(info["sd_model_name"])

    return inference["id"]


def get_inference_job(inference_id: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        'x-api-key': API_KEY
    }

    job = requests.get(STATUS_API_URL, headers=headers, params={"jobID": inference_id})

    return job.json()


def get_inference_param_output(inference_id: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        'x-api-key': API_KEY
    }

    job = requests.get(PARAM_API_URL, headers=headers, params={"jobID": inference_id})

    return job.json()


def get_inference_image_output(inference_id: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        'x-api-key': API_KEY
    }

    job = requests.get(IMAGE_API_URL, headers=headers, params={"jobID": inference_id})

    return job.json()


def get_checkpoints():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        'x-api-key': API_KEY
    }

    params = {
        "username": API_USERNAME,
        "status": "Active",
    }

    job = requests.get(CHECKPOINTS_API_URL, headers=headers, params=params)

    checkpoints = []
    if 'checkpoints' in job.json():
        for checkpoint in job.json()['checkpoints']:
            checkpoints.append(checkpoint['name'][0])

    if len(checkpoints) == 0:
        raise Exception("No checkpoint available.")

    global support_model_list
    support_model_list = checkpoints
    logger.info("support_model_list: {}".format(support_model_list))
    return support_model_list


def create_inference_job(models: List[str]):

    models = select_checkpoint(models)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        'x-api-key': API_KEY
    }

    # todo use default api params
    body = {
        "user_id": API_USERNAME,
        "task_type": "txt2img",
        "models": {
            "Stable-diffusion": models,
            "embeddings": []
        },
        "filters": {
            "createAt": datetime.now().timestamp(),
            "creator": "sd-webui"
        }
    }

    job = requests.post(GENERATE_API_URL, headers=headers, json=body)
    return job.json()


def run_inference_job(inference_id: str):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        'x-api-key': API_KEY
    }

    job = requests.put(COMMAND_API_URL + 'inference/v2/' + inference_id + '/run', headers=headers)

    return job.json()


def upload_inference_job_api_params(s3_url, positive: str, negative: str):
    # todo use default api params
    api_params = {
        "prompt": positive,
        "negative_prompt": negative,
        "styles": [],
        "seed": -1,
        "subseed": -1,
        "subseed_strength": 0.0,
        "seed_resize_from_h": -1,
        "seed_resize_from_w": -1,
        "sampler_name": "DPM++ 2M Karras",
        "batch_size": 1,
        "n_iter": 1,
        "steps": 20,
        "cfg_scale": 7.0,
        "width": 512,
        "height": 512,
        "restore_faces": None,
        "tiling": None,
        "do_not_save_samples": False,
        "do_not_save_grid": False,
        "eta": None,
        "denoising_strength": None,
        "s_min_uncond": 0.0,
        "s_churn": 0.0,
        "s_tmax": "Infinity",
        "s_tmin": 0.0,
        "s_noise": 1.0,
        "override_settings": {},
        "override_settings_restore_afterwards": True,
        "refiner_checkpoint": None,
        "refiner_switch_at": None,
        "disable_extra_networks": False,
        "comments": {},
        "enable_hr": False,
        "firstphase_width": 0,
        "firstphase_height": 0,
        "hr_scale": 2.0,
        "hr_upscaler": "Latent",
        "hr_second_pass_steps": 0,
        "hr_resize_x": 0,
        "hr_resize_y": 0,
        "hr_checkpoint_name": None,
        "hr_sampler_name": None,
        "hr_prompt": "",
        "hr_negative_prompt": "",
        "sampler_index": "DPM++ 2M Karras",
        "script_name": None,
        "script_args": [],
        "send_images": True,
        "save_images": False,
        "alwayson_scripts": {
            "refiner": {
                "args": [False, "", 0.8]
            },
            "seed": {
                "args": [-1, False, -1, 0, 0, 0]
            },
            "controlnet": {
                "args": [
                    {
                        "enabled": False,
                        "module": "none",
                        "model": "None",
                        "weight": 1,
                        "image": None,
                        "resize_mode": "Crop and Resize",
                        "low_vram": False,
                        "processor_res": -1,
                        "threshold_a": -1,
                        "threshold_b": -1,
                        "guidance_start": 0,
                        "guidance_end": 1,
                        "pixel_perfect": False,
                        "control_mode": "Balanced",
                        "is_ui": True,
                        "input_mode": "simple",
                        "batch_images": "",
                        "output_dir": "",
                        "loopback": False
                    },
                    {
                        "enabled": False,
                        "module": "none",
                        "model": "None",
                        "weight": 1,
                        "image": None,
                        "resize_mode": "Crop and Resize",
                        "low_vram": False,
                        "processor_res": -1,
                        "threshold_a": -1,
                        "threshold_b": -1,
                        "guidance_start": 0,
                        "guidance_end": 1,
                        "pixel_perfect": False,
                        "control_mode": "Balanced",
                        "is_ui": True,
                        "input_mode": "simple",
                        "batch_images": "",
                        "output_dir": "",
                        "loopback": False
                    },
                    {
                        "enabled": False,
                        "module": "none",
                        "model": "None",
                        "weight": 1,
                        "image": None,
                        "resize_mode": "Crop and Resize",
                        "low_vram": False,
                        "processor_res": -1,
                        "threshold_a": -1,
                        "threshold_b": -1,
                        "guidance_start": 0,
                        "guidance_end": 1,
                        "pixel_perfect": False,
                        "control_mode": "Balanced",
                        "is_ui": True,
                        "input_mode": "simple",
                        "batch_images": "",
                        "output_dir": "",
                        "loopback": False
                    }
                ]
            },
            "segment anything": {
                "args": [
                    False,
                    False,
                    0,
                    None,
                    [],
                    0,
                    False,
                    [],
                    [],
                    False,
                    0,
                    1,
                    False,
                    False,
                    0,
                    None,
                    [],
                    -2,
                    False,
                    [],
                    False,
                    0,
                    None,
                    None
                ]
            },
            "extra options": {
                "args": []
            }
        }
    }

    json_string = json.dumps(api_params)
    response = requests.put(s3_url, data=json_string)
    response.raise_for_status()
    return response


def generate_llm_image(initial_prompt: str, llm_prompt: bool, col, title: str):
    col.empty()
    col.subheader(title)
    st.spinner()
    st.session_state.progress = 5
    progress_bar = col.progress(st.session_state.progress)

    global support_model_list
    negative = ""
    models = default_models
    if llm_prompt is True:

        positive_prompt, negative_prompt, model_list = get_llm_processed_prompts(prompt)
        st.session_state.progress += 15
        progress_bar.progress(st.session_state.progress)

        # if prompt is empty, use default
        if positive_prompt != "":
            initial_prompt = positive_prompt

        if negative_prompt != "":
            negative = negative_prompt

        if len(model_list) > 0 and model_list[0] != "":
            models = model_list

    inference_id = generate_image(initial_prompt, negative, models, col, progress_bar)

    return inference_id


def select_checkpoint(user_list: List[str]):
    global support_model_list
    user_list = [item.strip() for item in user_list]
    intersection = list(set(user_list).intersection(set(support_model_list)))
    if len(intersection) == 0:
        intersection = default_models
        st.session_state.warning.append("Use default model {}\nwhen LLM recommends {} not in support list:\n{}".format(
            default_models, user_list, support_model_list))

    return intersection


# main entry point for debugging
# python -m streamlit run image_generation.py --server.port 8088
if __name__ == "__main__":
    try:
        st.set_page_config(layout="wide", page_title="Image Generation Application")

        st.title("Image Generation Application")

        # User input
        prompt = st.text_input("Enter a prompt for the image:", "A cute dog")

        button = st.button('Generate Image')

        col1, col2 = st.columns(2)

        # col1.subheader("Without LLM")
        # col1.image(Image.open("./zebra.jpg"))
        #
        # col2.subheader("With LLM")
        # col2.image(Image.open("./zebra.jpg"))

        if button:
            get_checkpoints()
            st.session_state.warning = []
            generate_llm_image(prompt, False, col1, "Without LLM")
            generate_llm_image(prompt, True, col2, "With LLM")

    except Exception as e:
        logger.exception(e)
        raise e
