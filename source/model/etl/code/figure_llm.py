import base64
import io
import json
import logging
import re

import boto3
from botocore.exceptions import ClientError

CHART_UNDERSTAND_PROMPT = """您是文档阅读专家。您的任务是将图片中的图表转换成Markdown格式。以下是说明：
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

IMAGE_DESCRIPTION_PROMPT = """
你是一位资深的图像分析专家。你的任务是仔细观察给出的插图,并按照以下步骤进行:
1. 清晰地描述这张图片中显示的内容细节。如果图片中包含任何文字,请确保在描述中准确无误地包含这些文字。
2. 使用<doc></doc>标签中的上下文信息来帮助你更好地理解和描述这张图片。上下文中的{tag}就是指该插图。
3. 将你的描述写在<output></output>标签之间。
<doc>
{context}
</doc>
请将你的描述写在<output></output>xml标签之间。
"""


class figureUnderstand:
    def __init__(
        self,
        model_provider="bedrock",
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        api_url=None,
        api_key=None,
    ):
        """
        Initialize the figureUnderstand class with configurable model provider.

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

        self.mermaid_prompt = json.load(open("prompt/mermaid.json", "r"))

    def invoke_llm(self, img, prompt, prefix="<output>", stop="</output>"):
        # Convert image to base64
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
        except ClientError as e:
            logging.error(f"Error invoking Bedrock model: {e}")
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
        except requests.exceptions.RequestException as e:
            logging.error(f"Error invoking {self.model_provider} API: {e}")
            raise

    def get_classification(self, img):
        with open("prompt/figure_classification.txt") as f:
            figure_classification_prompt = f.read()
        output = self.invoke_llm(img, figure_classification_prompt)
        return output

    def get_chart(self, img, context, tag):
        prompt = CHART_UNDERSTAND_PROMPT.strip()
        output = self.invoke_llm(img, prompt)
        return output

    def get_description(self, img, context, tag):
        prompt = IMAGE_DESCRIPTION_PROMPT.strip()

        output = self.invoke_llm(img, prompt.format(context=context, tag=tag))
        return f"![{output}]()"

    def get_mermaid(self, img, classification):
        with open("prompt/mermaid_template.txt") as f:
            mermaid_prompt = f.read()
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

    def __call__(self, img, context, tag, s3_link):
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
