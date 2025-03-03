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
import requests
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
s3_client = boto3.client("s3")


def get_api_key(api_secret_name):
    """
    Get the API key from AWS Secrets Manager.

    Args:
        api_secret_name (str): The name of the secret in AWS Secrets Manager containing the API key.

    Returns:
        str: The API key.
    """
    try:
        # Create a Secrets Manager client
        secrets_client = boto3.client("secretsmanager")
        # Get the secret value
        secret_response = secrets_client.get_secret_value(
            SecretId=api_secret_name
        )
        # Parse the secret JSON
        if "SecretString" in secret_response:
            secret_data = json.loads(secret_response["SecretString"])
            api_key = secret_data.get("key")
            logger.info(
                f"Successfully retrieved API key from secret: {api_secret_name}"
            )
            return api_key
    except Exception as e:
        logger.error(f"Error retrieving secret {api_secret_name}: {str(e)}")
    return None


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

    This class provides methods to analyze images using Claude 3 Sonnet model,
    classify them, and generate appropriate descriptions or representations.
    """

    def __init__(
        self,
        model_provider="bedrock",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        api_url=None,
        api_key=None,
    ):
        """Initialize the figureUnderstand class with configurable model provider.

        Args:
            model_provider (str): The model provider to use ('bedrock', 'openai', 'siliconflow', etc.)
            model_id (str): The model ID to use
            api_url (str, optional): The API URL for non-AWS providers
            api_key (str, optional): The API key for non-AWS providers
        """
        self.model_provider = model_provider.lower()
        self.model_id = model_id
        self.api_url = api_url
        self.api_key = api_key

        # Initialize appropriate client based on provider
        if self.model_provider == "bedrock":
            self.bedrock_runtime = boto3.client(service_name="bedrock-runtime")

        # Load mermaid prompt using the unified function
        self.mermaid_prompt = load_prompt_file("mermaid.json", is_json=True)

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

        if self.model_provider == "bedrock":
            return self._invoke_bedrock(base64_encoded, prompt, prefix, stop)
        elif self.model_provider in ["openai", "siliconflow"]:
            return self._invoke_openai_compatible(
                base64_encoded, prompt, prefix, stop
            )
        else:
            raise ValueError(
                f"Unsupported model provider: {self.model_provider}"
            )

    def _invoke_bedrock(self, base64_encoded, prompt, prefix, stop):
        """Invoke Bedrock models"""
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

        try:
            response = self.bedrock_runtime.invoke_model(
                body=body, modelId=self.model_id
            )
            response_body = json.loads(response.get("body").read())
            result = prefix + response_body["content"][0]["text"] + stop
            return result
        except Exception as e:
            logger.error(f"Error invoking Bedrock model: {e}")
            raise

    def _invoke_openai_compatible(self, base64_encoded, prompt, prefix, stop):
        """Invoke OpenAI-compatible API (OpenAI, SiliconFlow, etc.)"""
        import requests

        if not self.api_url or not self.api_key:
            raise ValueError(
                "API URL and API key are required for OpenAI-compatible providers"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_encoded}",
                            },
                        },
                    ],
                },
                {"role": "assistant", "content": prefix},
            ],
            "max_tokens": 4096,
            "stop": [stop],
        }

        try:
            response = requests.post(
                self.api_url, json=payload, headers=headers
            )
            response.raise_for_status()
            response_data = response.json()

            # Extract text from response based on OpenAI format
            result = (
                prefix
                + response_data["choices"][0]["message"]["content"]
                + stop
            )
            return result
        except Exception as e:
            logger.error(f"Error invoking {self.model_provider} API: {e}")
            raise

    def get_classification(self, img):
        figure_classification_prompt = load_prompt_file(
            "figure_classification.txt"
        )
        output = self.invoke_llm(img, figure_classification_prompt)
        return output

    def get_chart(self, img, context, tag):
        prompt = CHART_UNDERSTAND_PROMPT.strip()
        output = self.invoke_llm(img, prompt)
        return output

    def get_description(self, img, context, tag):
        prompt = DESCRIPTION_PROMPT.strip()

        output = self.invoke_llm(img, prompt.format(context=context, tag=tag))
        return f"![{output}]()"

    def get_mermaid(self, img, classification):
        mermaid_prompt = load_prompt_file("mermaid_template.txt")
        prompt = mermaid_prompt.format(
            diagram_type=classification,
            diagram_example=self.mermaid_prompt[classification],
        )
        output = self.invoke_llm(
            img, prompt, prefix="<description>", stop="</mermaid>"
        )
        return output

    def parse_result(self, llm_output, tag):
        try:
            pattern = rf"<{tag}>(.*?)</{tag}>"
            output = re.findall(pattern, llm_output, re.DOTALL)[0].strip()
        except:
            output = llm_output.replace(f"<{tag}>", "").replace(f"</{tag}>", "")
        return output

    def figure_understand(self, img, context, tag, s3_link):
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
    is_bytes: bool = False,
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

    if is_bytes:
        s3_client.put_object(Bucket=bucket, Key=object_key, Body=image_data)
    else:
        s3_client.upload_file(image_data, bucket, object_key)

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
    model_provider: str = "bedrock",
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
    api_url: str = None,
    api_key: str = None,
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
        model_provider=model_provider,
        model_id=model_id,
        api_url=api_url,
        api_key=api_key,
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
    content: str, bucket_name: str, file_name: str, **kwargs
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
    model_provider = kwargs.get("model_provider")
    model_id = kwargs.get("model_id")
    api_url = kwargs.get("api_url")
    api_secret_name = kwargs.get("api_secret_name")

    if api_secret_name:
        api_key = get_api_key(api_secret_name)
    else:
        api_key = None

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
            # Handle local images from docx
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
                model_provider,
                model_id,
                api_url,
                api_key,
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
