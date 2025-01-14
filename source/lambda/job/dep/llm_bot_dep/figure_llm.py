import base64
import io
import json
import logging
import os
import re
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

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

MERMAID_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompt/mermaid.json")
FIGURE_CLASSIFICATION_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompt/figure_classification.txt")
MERMAID_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "prompt/mermaid_template.txt")

logger = logging.getLogger(__name__)
s3_client = boto3.client("s3")


class figureUnderstand:
    def __init__(self):
        self.bedrock_runtime = boto3.client(service_name="bedrock-runtime")
        self.mermaid_prompt = json.load(open(MERMAID_PROMPT_PATH, "r"))

    def invoke_llm(self, img, prompt, prefix="<output>", stop="</output>"):
        # If img is already a base64 string, use it directly
        if isinstance(img, str):
            base64_encoded = img
        else:
            # If img is a PIL Image, convert it to base64
            image_stream = io.BytesIO()
            img.save(image_stream, format="JPEG")
            base64_encoded = base64.b64encode(image_stream.getvalue()).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_encoded}},
                    {"type": "text", "text": prompt},
                ],
            },
            {"role": "assistant", "content": prefix},
        ]
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "stop_sequences": [stop],
            }
        )
        response = self.bedrock_runtime.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get("body").read())
        result = prefix + response_body["content"][0]["text"] + stop
        return result

    def get_classification(self, img):
        with open(FIGURE_CLASSIFICATION_PROMPT_PATH) as f:
            figure_classification_prompt = f.read()
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
        with open(MERMAID_TEMPLATE_PATH) as f:
            mermaid_prompt = f.read()
        prompt = mermaid_prompt.format(diagram_type=classification, diagram_example=self.mermaid_prompt[classification])
        output = self.invoke_llm(img, prompt, prefix="<description>", stop="</mermaid>")
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
            output = (
                f"\n<figure>\n<type>image</type>\n<link>{s3_link}</link>\n<desp>\n{description}\n</desp>\n</figure>\n"
            )
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


def upload_image_to_s3(image_path: str, bucket: str, file_name: str, splitting_type: str, idx: int):
    # round the timestamp to hours to avoid too many folders
    hour_timestamp = datetime.now().strftime("%Y-%m-%d-%H")
    image_name = f"{idx:05d}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.jpg"
    object_key = f"{file_name}/{splitting_type}/{hour_timestamp}/{image_name}"
    s3_client.upload_file(image_path, bucket, object_key)
    return object_key


def process_markdown_images_with_llm(content: str, bucket_name: str, file_name: str) -> str:
    """Process images in markdown content and upload them to S3.

    Args:
        content (str): The markdown content containing images to process
        bucket_name (str): The S3 bucket where images will be uploaded
        file_name (str): The file name for organizing uploads

    Returns:
        str: Processed markdown with updated image references
    """
    figure_llm = figureUnderstand()

    # Regular expression to find markdown image syntax: ![alt text](image_path)
    image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"

    # Keep track of where we last ended to maintain the full text
    last_end = 0
    result = ""

    for idx, match in enumerate(re.finditer(image_pattern, content), 1):
        # Generate unique identifier for this image
        image_tag = f"[IMAGE_{idx:05d}]"

        # Get the full image match and its position
        start, end = match.span()
        img_path = match.group(2)  # Get the image path from the markdown syntax

        # Add the text before the image
        result += content[last_end:start]

        # Get context (200 characters before and after)
        context_start = max(0, start - 200)
        context_end = min(len(content), end + 200)
        context = f"{content[context_start:start]}\n<image>\n{image_tag}\n</image>\n{content[end:context_end]}"

        try:
            # Convert image to base64
            image_base64 = encode_image_to_base64(img_path)

            # Get image understanding
            understanding = figure_llm.figure_understand(image_base64, context, image_tag, s3_link=f"{idx:05d}.jpg")

            updated_s3_link = upload_image_to_s3(img_path, bucket_name, file_name, "image", idx)
            understanding = understanding.replace(f"<link>{idx:05d}.jpg</link>", f"<link>{updated_s3_link}</link>")

            # Add the understanding text
            result += f"\n\n{understanding}\n\n"

        except Exception as e:
            logger.error(f"Error processing image {idx}: {e}")
            # If there's an error, keep the original markdown image syntax
            result += match.group(0)

        last_end = end

    # Add any remaining text after the last image
    result += content[last_end:]

    return result
