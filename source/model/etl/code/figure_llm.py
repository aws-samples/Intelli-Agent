import base64
import io
import json
import logging
import re

import boto3
from openai import OpenAI

# Add logger configuration
logger = logging.getLogger(__name__)

BEDROCK_CROSS_REGION_SUPPORTED_REGIONS = [
    "us-east-1",
    "us-west-2",
    "eu-central-1",
    "eu-west-1",
    "eu-west-3",
]


class figureUnderstand:
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
        if model_provider == "Bedrock":
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
        elif model_provider == "OpenAI API":
            self.openai_api_key = self._get_api_key(model_secret_name)

            self.model_id = model_id

            self.openai_client = OpenAI(
                api_key=self.openai_api_key, base_url=model_api_url
            )

        elif model_provider == "SageMaker":
            self.sagemaker_client = boto3.client("sagemaker-runtime")
            self.model_sagemaker_endpoint_name = model_sagemaker_endpoint_name
        else:
            raise ValueError(
                "Unsupported model provider. Choose 'Bedrock' or 'OpenAI API' or 'SageMaker'"
            )

        self.mermaid_prompt = json.load(open("prompt/mermaid.json", "r"))

    def _get_api_key(self, api_secret_name):
        """
        Get the API key from AWS Secrets Manager.
        Args:
            api_secret_name (str): The name of the secret in AWS Secrets Manager containing the API key.
        Returns:
            str: The API key.
        """
        if not api_secret_name:
            logger.error(
                "API secret name is required for OpenAI integration. Multimodal image processing will be unavailable."
            )
            return None
        try:
            secrets_client = boto3.client("secretsmanager")
            secret_response = secrets_client.get_secret_value(
                SecretId=api_secret_name
            )
            if "SecretString" in secret_response:
                secret_data = json.loads(secret_response["SecretString"])
                api_key = secret_data.get("key")
                logger.info(
                    f"Successfully retrieved API credentials from secret: {api_secret_name}"
                )
                return api_key
        except Exception as e:
            logger.error(
                f"Failed to retrieve secret '{api_secret_name}': {str(e)}. Multimodal image processing will be unavailable."
            )
            return None

    def _image_to_base64(self, img):
        """Convert PIL Image to base64 encoded string"""
        image_stream = io.BytesIO()
        img.save(image_stream, format="JPEG")
        return base64.b64encode(image_stream.getvalue()).decode("utf-8")

    def invoke_llm(self, img, prompt, prefix="<output>", stop="</output>"):
        if self.model_provider == "Bedrock":
            return self._invoke_bedrock(img, prompt, prefix, stop)
        elif self.model_provider == "OpenAI API":
            return self._invoke_openai(img, prompt, prefix, stop)
        elif self.model_provider == "SageMaker":
            return self._invoke_sagemaker(img, prompt, prefix, stop)

    def _invoke_bedrock(self, img, prompt, prefix="<output>", stop="</output>"):
        base64_encoded = self._image_to_base64(img)
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
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key not configured. Please provide a valid API secret name."
            )
        base64_encoded = self._image_to_base64(img)

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
        with open("prompt/figure_classification.txt") as f:
            figure_classification_prompt = f.read()
        output = self.invoke_llm(img, figure_classification_prompt)
        return output

    def get_chart(self, img, context, tag):
        with open("prompt/chart.txt") as f:
            chart_prompt = f.read()
        output = self.invoke_llm(
            img, chart_prompt.format(context=context, tag=tag)
        )
        return output

    def get_description(self, img, context, tag):
        with open("prompt/description.txt") as f:
            description_prompt = f.read()
        output = self.invoke_llm(
            img, description_prompt.format(context=context, tag=tag)
        )
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
