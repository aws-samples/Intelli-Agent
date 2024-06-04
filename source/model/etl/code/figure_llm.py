from anthropic import AnthropicBedrock
import re
import io
import base64

class figureUnderstand():
    def __init__(self):
        self.client = AnthropicBedrock(
            aws_region="us-west-2",
        )
    def invoke_llm(self, img, prompt):
        image_stream = io.BytesIO()
        img.save(image_stream, format="JPEG")
        base64_encoded = base64.b64encode(image_stream.getvalue()).decode('utf-8')
        messages = [
          {
            "role": "user",
            "content": [
              {
                "type": "image",
                "source": {
                  "type": "base64",
                  "media_type": "image/jpeg",
                  "data": base64_encoded
                }
              },
              {
                "type": "text",
                "text": prompt
              }
            ]
          },
          {"role": "assistant", "content": "<output>"},
        ]
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        message = self.client.messages.create(
            model=model_id, max_tokens=4096, messages=messages
        )
        result = '<output>' + message.content[0].text
        try:
            pattern = r"<output>(.*?)</output>"
            output = re.findall(pattern, result, re.DOTALL)[0].strip()
        except:
            output = result.replace('<output>', '').replace('</output>', '')
        return output
    def get_classification(self, img):
        prompt = '''
您的任务是判断给定的图片是否为图表。请仔细查看图片。如果该图片是一个图表,请在<output></output>XML标签中输出"Y"。如果该图片不是图表,请在<output></output>XML标签中输出"N"。

1. 仔细观察给定的图片
2. 检查图片是否包含图形元素,比如条形图、折线图、饼图等
3. 如果图片包含这些元素,则将其归类为图表
4. 在<output></output>标签中输出"Y"或"N"
'''.strip()
        output = self.invoke_llm(img, prompt)
        return True if output == 'Y' else False
    def get_chart(self, img, context, tag):
        prompt = '''您是文档阅读专家。您的任务是将图片中的图表转换成Markdown格式。以下是说明：
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
'''.strip()
        output = self.invoke_llm(img, prompt)
        return output
    def get_description(self, img, context, tag):
        prompt = '''
你是一位资深的图像分析专家。你的任务是仔细观察给出的插图,并按照以下步骤进行:
1. 清晰地描述这张图片中显示的内容细节。如果图片中包含任何文字,请确保在描述中准确无误地包含这些文字。
2. 使用<doc></doc>标签中的上下文信息来帮助你更好地理解和描述这张图片。上下文中的{tag}就是指该插图。
3. 将你的描述写在<output></output>标签之间。
<doc>
{context}
</doc>
请将你的描述写在<output></output>xml标签之间。
'''.strip()
        
        output = self.invoke_llm(img, prompt.format(context=context, tag=tag))
        return f'![{output}]()'
    def __call__(self, img, context, tag):
        classification = self.get_classification(img)
        if classification:
            output = self.get_chart(img, context, tag)
        else:
            output = self.get_description(img, context, tag)
        return output