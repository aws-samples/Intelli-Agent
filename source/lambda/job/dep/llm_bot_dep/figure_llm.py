import base64
import importlib.resources
import io
import json
import logging
import mimetypes
import os
import re
import tempfile
from datetime import datetime
from typing import Union

import boto3
import openai
import requests
from llm_bot_dep.schemas.processing_parameters import VLLMParameters
from llm_bot_dep.utils.s3_utils import upload_file_to_s3
from llm_bot_dep.utils.secrets_manager_utils import get_api_key
from PIL import Image

CHART_UNDERSTAND_PROMPT = """
您是文档阅读专家。您的任务是将图片中的图表转换成Markdown格式。以下是说明：
1. 找到图片中的图表。
2. 仔细观察图表，了解其中包含的结构和数据。
3. 使用<doc></doc>标签中的上下文信息来帮助你更好地理解和描述这张图表。上下文中的{tag}就是指该图表。
4. 按照以下指南将图表数据转换成 Markdown 表格格式：
    - 使用 | 字符分隔列
    - 使用 --- 行表示标题行
    - 确保表格格式正确并对齐
    - 对于不确定的数字，请根据图片估算。
5. 仔细检查您的 Markdown 表格是否准确地反映了图表图像中的数据。
6. 在 <output></output>xml 标签中仅返回 Markdown，不含其他文本。

<doc>
{context}
</doc>
请将你的描述写在<output></output>xml标签之间。
"""

DESCRIPTION_PROMPT = """
你是一位资深的图像分析专家。你的任务是仔细观察给出的插图,并按照以下步骤进行:
1. 清晰地描述这张图片中显示的内容细节。如果图片中包含任何文字,请确保在描述中准确无误地包含这些文字。
2. 使用<doc></doc>标签中的上下文信息来帮助你更好地理解和描述这张图片。上下文中的{tag}就是指该插图。
3. 将你的描述写在<output></output>标签之间。
<doc>
{context}
</doc>
请将你的描述写在<output></output>xml标签之间。
"""

# Add minimum size threshold constants
MIN_WIDTH = 50  # minimum width in pixels
MIN_HEIGHT = 50  # minimum height in pixels

logger = logging.getLogger(__name__)

BEDROCK_CROSS_REGION_SUPPORTED_REGIONS = [
    "us-east-1",
    "us-west-2",
    "eu-central-1",
    "eu-west-1",
    "eu-west-3",
]


def load_prompt_file(file_path, is_json=False):
    """Load a prompt file from package resources or file system.

    Args:
        file_path (str): Path to the prompt file relative to the package
        is_json (bool): Whether to parse the file as JSON

    Returns:
        The content of the prompt file, parsed as JSON if is_json=True
    """
    try:
        with importlib.resources.files("llm_bot_dep.prompt").joinpath(
            file_path
        ).open("r") as file:
            if is_json:
                data = json.load(file)
            else:
                data = file.read()
        return data
    except (ImportError, ModuleNotFoundError, FileNotFoundError):
        # Fallback for older Python versions or direct file access
        raise FileNotFoundError(f"Prompt file not found: {file_path}")


class figureUnderstand:
    """A class to understand and process figures using LLM.

    This class provides methods to analyze images using Claude 3 Sonnet model or OpenAI models,
    classify them, and generate appropriate descriptions or representations.
    """

    def __init__(
        self,
        model_provider="bedrock",
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        model_api_url="",
        model_secret_name="",
        model_sagemaker_endpoint_name="",
    ):
        """Initialize the figureUnderstand class with appropriate client.

        Args:
            model_provider (str): The LLM provider to use ('bedrock' or 'openai')
            model_id (str): The model ID to use
            model_api_url (str): The API URL for OpenAI
            model_secret_name (str): Secret name for OpenAI API key (required for OpenAI)
            model_sagemaker_endpoint_name (str): The name of the SageMaker endpoint for the model
        """
        self.model_provider = model_provider
        if model_provider == "bedrock":
            session = boto3.session.Session()
            bedrock_region = session.region_name

            # Validate region support
            if bedrock_region not in BEDROCK_CROSS_REGION_SUPPORTED_REGIONS:
                raise ValueError(
                    f"Bedrock is not supported in region {bedrock_region}"
                )

            # Initialize Bedrock client and model ID
            self.bedrock_runtime = boto3.client(service_name="bedrock-runtime")

            # Add model prefix if not provided
            model_prefix = bedrock_region.split("-")[0] + "."
            if not model_id.startswith(model_prefix):
                model_id = model_prefix + model_id
            self.model_id = model_id
        elif model_provider == "openai":
            self.openai_api_key = get_api_key(model_secret_name)
            if not self.openai_api_key:
                raise ValueError(
                    f"Failed to retrieve OpenAI API key from Secrets Manager. Please check the secret name: {model_secret_name}"
                )

            openai.api_key = self.openai_api_key
            openai.base_url = model_api_url
            self.model_id = model_id

            self.openai_client = openai
        elif model_provider == "sagemaker":
            if (
                not model_sagemaker_endpoint_name
                or model_sagemaker_endpoint_name == "-"
            ):
                raise ValueError(
                    "SageMaker endpoint name is required when using SageMaker model"
                )
            self.sagemaker_client = boto3.client("sagemaker-runtime")
            self.model_sagemaker_endpoint_name = model_sagemaker_endpoint_name
        else:
            raise ValueError(
                "Unsupported model provider. Choose 'bedrock' or 'openai'"
            )

        self.mermaid_prompt = load_prompt_file("mermaid.json", is_json=True)
        self.figure_classification_prompt = load_prompt_file(
            "figure_classification.txt"
        )
        self.mermaid_template_prompt = load_prompt_file("mermaid_template.txt")

    def invoke_llm(self, img, prompt, prefix="<output>", stop="</output>"):
        """Invoke the LLM model with an image and prompt.

        Args:
            img: Either a base64 encoded string or PIL Image object
            prompt (str): The prompt to send to the model
            prefix (str): Starting tag for the output
            stop (str): Ending tag for the output

        Returns:
            str: The model's response with prefix and stop tags
        """
        if self.model_provider == "bedrock":
            return self._invoke_bedrock(img, prompt, prefix, stop)
        elif self.model_provider == "openai":
            return self._invoke_openai(img, prompt, prefix, stop)
        elif self.model_provider == "sagemaker":
            return self._invoke_sagemaker(img, prompt, prefix, stop)

    def _invoke_bedrock(self, img, prompt, prefix="<output>", stop="</output>"):
        """Invoke Bedrock model with image and prompt."""
        # If img is already a base64 string, use it directly
        if isinstance(img, str):
            base64_encoded = img
        else:
            # If img is a PIL Image, convert it to base64
            image_stream = io.BytesIO()
            img.save(image_stream, format="JPEG")
            base64_encoded = base64.b64encode(image_stream.getvalue()).decode(
                "utf-8"
            )

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_encoded,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
            {"role": "assistant", "content": prefix},
        ]
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "stop_sequences": [stop],
            }
        )
        response = self.bedrock_runtime.invoke_model(
            body=body, modelId=self.model_id
        )
        response_body = json.loads(response.get("body").read())
        result = prefix + response_body["content"][0]["text"] + stop
        return result

    def _invoke_openai(self, img, prompt, prefix="<output>", stop="</output>"):
        """Invoke OpenAI model with image and prompt."""
        # If img is already a base64 string, use it directly
        if isinstance(img, str):
            base64_encoded = img
        else:
            # If img is a PIL Image, convert it to base64
            image_stream = io.BytesIO()
            img.save(image_stream, format="JPEG")
            base64_encoded = base64.b64encode(image_stream.getvalue()).decode(
                "utf-8"
            )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_encoded}"
                        },
                    },
                ],
            },
            {"role": "assistant", "content": prefix},
        ]

        response = self.openai_client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            max_tokens=4096,
            stop=[stop] if stop else None,
        )

        result = prefix + response.choices[0].message.content + stop
        return result

    def _invoke_sagemaker(
        self, img, prompt, prefix="<output>", stop="</output>"
    ):
        """Invoke SageMaker model with image and prompt."""
        # If img is already a base64 string, use it directly
        if isinstance(img, str):
            base64_encoded = img
        else:
            # If img is a PIL Image, convert it to base64
            image_stream = io.BytesIO()
            img.save(image_stream, format="JPEG")
            base64_encoded = base64.b64encode(image_stream.getvalue()).decode(
                "utf-8"
            )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_encoded}"
                        },
                    },
                ],
            },
            {"role": "assistant", "content": prefix},
        ]

        payload = {
            "messages": messages,
            "stream": False,
        }

        response = self.sagemaker_client.invoke_endpoint(
            EndpointName=self.model_sagemaker_endpoint_name,
            Body=json.dumps(payload),
            ContentType="application/json",
        )
        response_body = response["Body"].read().decode("utf-8")
        response_json = json.loads(response_body)
        result = (
            prefix + response_json["choices"][0]["message"]["content"] + stop
        )
        return result

    def get_classification(self, img):
        """Get image classification from LLM."""
        output = self.invoke_llm(img, self.figure_classification_prompt)
        return output

    def get_chart(self, img, context, tag):
        """Get chart data from image."""
        prompt = CHART_UNDERSTAND_PROMPT.strip()
        output = self.invoke_llm(img, prompt.format(context=context, tag=tag))
        return output

    def get_description(self, img, context, tag):
        """Get image description from LLM."""
        prompt = DESCRIPTION_PROMPT.strip()
        output = self.invoke_llm(img, prompt.format(context=context, tag=tag))
        return f"![{output}]()"

    def get_mermaid(self, img, classification):
        """Get mermaid diagram from image."""
        prompt = self.mermaid_template_prompt.format(
            diagram_type=classification,
            diagram_example=self.mermaid_prompt[classification],
        )
        output = self.invoke_llm(
            img, prompt, prefix="<description>", stop="</mermaid>"
        )
        return output

    def parse_result(self, llm_output, tag):
        """Parse LLM output to extract content between tags."""
        try:
            pattern = rf"<{tag}>(.*?)</{tag}>"
            output = re.findall(pattern, llm_output, re.DOTALL)[0].strip()
        except:
            output = llm_output.replace(f"<{tag}>", "").replace(f"</{tag}>", "")
        return output

    def figure_understand(self, img, context, tag, s3_link):
        """Process image and generate appropriate representation based on classification.

        This is the main method that orchestrates the image understanding process.
        """
        classification = self.get_classification(img)
        classification = self.parse_result(classification, "output")
        if classification in self.mermaid_prompt:
            mermaid_output = self.get_mermaid(img, classification)
            description = self.parse_result(mermaid_output, "description")
            mermaid_code = self.parse_result(mermaid_output, "mermaid")
            if classification in ("XY Chart", "Pie chart diagrams"):
                table = self.get_chart(img, context, tag)
                table = self.parse_result(table, "output")
                output = f"\n<figure>\n<type>chart</type>\n<link>{s3_link}</link>\n<desp>\n{description}\n</desp>\n<value>\n{table}\n</value>\n</figure>\n"
            else:
                output = f"\n<figure>\n<type>chart-mermaid</type>\n<link>{s3_link}</link>\n<desp>\n{description}\n</desp>\n<value>\n{mermaid_code}\n</value>\n</figure>\n"
        else:
            description = self.get_description(img, context, tag)
            description = self.parse_result(description, "output")
            output = f"\n<figure>\n<type>image</type>\n<link>{s3_link}</link>\n<desp>\n{description}\n</desp>\n</figure>\n"
        return output

    # Add compatibility with the __call__ method from the ETL version
    __call__ = figure_understand


def encode_image_to_base64(image_path: str) -> str:
    """Convert a local image file to base64 string.

    Args:
        image_path (str): Path to the local image file

    Returns:
        str: Base64 encoded string of the image

    Raises:
        FileNotFoundError: If the image file doesn't exist
        Exception: For other errors during image processing
    """
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            return base64.b64encode(image_data).decode("utf-8")
    except Exception as e:
        logger.error(f"Error converting image to base64: {e}")
        raise


def upload_image_to_s3(
    image_data: Union[str, bytes],
    bucket: str,
    file_name: str,
    splitting_type: str,
    idx: int,
):
    """Upload image to S3 from either a file path or binary data.

    Args:
        image_data: Either a file path (str) or image binary data (bytes)
        bucket: S3 bucket name
        file_name: Base file name for S3 path
        splitting_type: Type of splitting being performed
        idx: Index number of the image
        is_bytes: Whether image_data contains binary data instead of a file path
    """
    hour_timestamp = datetime.now().strftime("%Y-%m-%d-%H")
    image_name = (
        f"{idx:05d}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.jpg"
    )
    object_key = f"{file_name}/{splitting_type}/{hour_timestamp}/{image_name}"

    upload_file_to_s3(bucket, object_key, image_data)

    return object_key


def download_image_from_url(img_url: str) -> str:
    """Download image from URL and save to temporary file.

    Returns:
        str: Path to temporary file containing the image
    """
    response = requests.get(img_url, timeout=10)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    ext = mimetypes.guess_extension(content_type) or ".jpg"
    if ext == ".jpe":
        ext = ".jpg"

    temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_file.write(response.content)
    temp_file.close()
    return temp_file.name


def process_single_image(
    img_path: str,
    context: str,
    image_tag: str,
    bucket_name: str,
    file_name: str,
    idx: int,
    s3_link: str = None,
    vllm_params: VLLMParameters = None,
) -> str:
    """Process a single image and return its understanding text.

    Args:
        img_path (str): Path to the image file
        context (str): Surrounding text context for the image
        image_tag (str): Tag to identify the image in the context
        bucket_name (str): S3 bucket name for uploading
        file_name (str): Base file name for S3 path
        idx (int): Index number of the image

    Returns:
        str: The processed understanding text for the image, or None if image is too small

    Raises:
        Various exceptions during image processing and upload
    """
    with Image.open(img_path) as img:
        width, height = img.size
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            logger.warning(
                f"Image {idx} is too small ({width}x{height}). Skipping processing."
            )
            return None

    image_base64 = encode_image_to_base64(img_path)
    figure_llm = figureUnderstand(
        model_provider=vllm_params.model_provider,
        model_id=vllm_params.model_id,
        model_api_url=vllm_params.model_api_url,
        model_secret_name=vllm_params.model_secret_name,
        model_sagemaker_endpoint_name=vllm_params.model_sagemaker_endpoint_name,
    )

    # Get image understanding
    understanding = figure_llm.figure_understand(
        image_base64, context, image_tag, s3_link=f"{idx:05d}.jpg"
    )

    # Update S3 link
    if not s3_link:
        s3_link = upload_image_to_s3(
            img_path, bucket_name, file_name, "image", idx
        )

    understanding = understanding.replace(
        f"<link>{idx:05d}.jpg</link>", f"<link>{s3_link}</link>"
    )

    return understanding, s3_link


def process_markdown_images_with_llm(
    content: str, bucket_name: str, file_name: str, vllm_params: VLLMParameters
) -> str:
    """Process all images in markdown content and upload them to S3.

    This function:
    1. Finds all markdown image references in the content
    2. Downloads images if they are URLs
    3. Processes each image with LLM
    4. Uploads images to S3
    5. Replaces image references with processed understanding

    Args:
        content (str): The markdown content containing images
        bucket_name (str): S3 bucket name for uploading
        file_name (str): Base file name for S3 path

    Returns:
        str: Updated content with processed image understandings
    """
    # Regular expression to find markdown image syntax: ![alt text](image_path)
    image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    last_end = 0
    result = ""
    # Add mapping to track image paths and their S3 objects
    image_s3_mapping = {}

    for idx, match in enumerate(re.finditer(image_pattern, content), 1):
        start, end = match.span()
        img_path = match.group(2)
        image_tag = f"[IMAGE_{idx:05d}]"

        # Add the text before the image
        result += content[last_end:start]

        try:
            # Handle URL images
            if img_path.startswith(("http://", "https://")):
                try:
                    local_img_path = download_image_from_url(img_path)
                except Exception as e:
                    logger.error(
                        f"Error downloading image from URL {img_path}: {e}"
                    )
                    result += match.group(1)
                    last_end = end
                    continue
            elif img_path.startswith("/tmp/doc_images/"):
                local_img_path = img_path
            else:
                logger.error(f"Image path {img_path} is not a URL")
                result += match.group(1)
                last_end = end
                continue

            # Get context
            context_start = max(0, start - 200)
            context_end = min(len(content), end + 200)
            context = f"{content[context_start:start]}\n<image>\n{image_tag}\n</image>\n{content[end:context_end]}"

            # Check if image was already processed
            s3_link = image_s3_mapping.get(img_path)

            # Process the image
            understanding, updated_s3_link = process_single_image(
                local_img_path,
                context,
                image_tag,
                bucket_name,
                file_name,
                idx,
                s3_link,
                vllm_params,
            )

            # If this is a new image path, store its S3 object name
            if not s3_link and understanding:
                image_s3_mapping[img_path] = updated_s3_link

            if understanding:
                result += f"\n\n{understanding}\n\n"
            else:
                result += match.group(1)

        except Exception as e:
            logger.error(f"Error processing image {idx}: {e}")
            result += match.group(1)

        last_end = end

    # Add any remaining text after the last image
    result += content[last_end:]
    return result
