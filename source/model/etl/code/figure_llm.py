import base64
import io
import json
import os

import openai

# Add logger configuration
logger = logging.getLogger(__name__)


class figureUnderstand:
    def __init__(self, model_provider="bedrock", api_secret_name=None):
        self.model_provider = model_provider
        if model_provider == "bedrock":
            self.bedrock_runtime = boto3.client(service_name="bedrock-runtime")
        elif model_provider == "openai":
            self.openai_api_key = self._get_api_key(api_secret_name)
            if not self.openai_api_key:
                raise ValueError(
                    "Failed to retrieve OpenAI API key from Secrets Manager"
                )
            openai.api_key = self.openai_api_key
            # Set OpenAI base URL from environment variable if provided
            base_url = os.environ.get("OPENAI_API_BASE")
            if base_url:
                openai.base_url = base_url
        else:
            raise ValueError(
                "Unsupported model provider. Choose 'bedrock' or 'openai'"
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
            raise ValueError(
                "api_secret_name must be provided when using OpenAI"
            )

        try:
            secrets_client = boto3.client("secretsmanager")
            secret_response = secrets_client.get_secret_value(
                SecretId=api_secret_name
            )
            if "SecretString" in secret_response:
                secret_data = json.loads(secret_response["SecretString"])
                api_key = secret_data.get("api_key")
                logger.info(
                    f"Successfully retrieved API key from secret: {api_secret_name}"
                )
                return api_key
        except Exception as e:
            logger.error(f"Error retrieving secret {api_secret_name}: {str(e)}")
            raise
        return None

    def _image_to_base64(self, img):
        """Convert PIL Image to base64 encoded string"""
        image_stream = io.BytesIO()
        img.save(image_stream, format="JPEG")
        return base64.b64encode(image_stream.getvalue()).decode("utf-8")

    def invoke_llm(self, img, prompt, prefix="<output>", stop="</output>"):
        if self.model_provider == "bedrock":
            return self._invoke_bedrock(img, prompt, prefix, stop)
        elif self.model_provider == "openai":
            return self._invoke_openai(img, prompt, prefix, stop)

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
        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages,
                "stop_sequences": [stop],
            }
        )
        response = self.bedrock_runtime.invoke_model(
            body=body, modelId=model_id
        )
        response_body = json.loads(response.get("body").read())
        result = prefix + response_body["content"][0]["text"] + stop
        return result

    def _invoke_openai(self, img, prompt, prefix="<output>", stop="</output>"):
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

        response = openai.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=4096,
            stop=[stop] if stop else None,
        )

        result = prefix + response.choices[0].message.content + stop
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
