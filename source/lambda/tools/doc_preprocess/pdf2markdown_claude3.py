import boto3
import base64
import io
import json
import os
import argparse
from tqdm import tqdm
from PIL import Image
from typing import Any, Dict, List, Optional, Mapping
from pdf2image import convert_from_path

def format_to_message(query:str, image_base64_list:List[str]=None, role:str = "user"):
    if image_base64_list:
        content = [{ "type": "image", "source": { "type": "base64", "media_type": "image/png", "data": image_base64 }} for image_base64 in image_base64_list ]
        content.append({ "type": "text", "text": query })
        return { "role": role, "content": content }

    return {"role": role, "content": query }

def Image2base64(img_path):
    image = Image.open(img_path)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_data = buffer.getvalue()
    base64_encoded_string = base64.b64encode(image_data).decode('utf-8')

    return base64_encoded_string

def construct_multimodal_prompt(img_path):
    prompt = """Please help me organize the content on the picture into text. 

<requirements>
1. Based on the layout in the image, determine the output order. If there is no explicit order, convert the text part first, then the chart part.
2. Output in markdown format. Try your best to keep all the information(text, format, chart).
4. Pay attention to the formatting, keep the the quote and header level. 
5. convert image to markdown picture tag, describe image in image name, for example "![description](url placeholder)"
6. convert table into markdown table format
7. convert bar chart into bullets format, use Chart Title as Title, Category Label as bullet header, Value Labels as value, keep all category labels.
8. convert pie chart into bullets format, use Chart Title as Title, Category Label as bullet header, Value Labels as value, keep all category labels.
9. Be consistent with the original language in pictures.

</requirements>
put your output between <output> and </output>"""

    base64_image = Image2base64(img_path)
    message = format_to_message(prompt, [base64_image])

    messages = [ message, { "role":"assistant", "content": "<output>"} ]

    input_body = {}
    input_body["anthropic_version"] = "bedrock-2023-05-31"
    input_body["messages"] = messages
    input_body["max_tokens"] = 4096
    input_body["stop_sequences"] = ['</output>']

    body = json.dumps(input_body)

    return body

def convert2markdown(img_path):
    md_result = ""
    try:
        request_body = construct_multimodal_prompt(img_path)
        request_options = {
            "body": request_body,
            "modelId": 'anthropic.claude-3-sonnet-20240229-v1:0',
            "accept": "application/json",
            "contentType": "application/json",
        }

        response = boto3_bedrock.invoke_model(**request_options)

        body = response.get('body').read().decode('utf-8')

        body_dict = json.loads(body)

        md_result = body_dict['content'][0].get("text")
    except Exception as e:
        print(f"failed to process {img_path}")
        print(e)

    return md_result

def pdf2image(input_dir, output_dir):
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.pdf'):
                print(f"skip {file}..")
                continue
            # 构造文件的完整路径
            file_path = os.path.join(root, file)
            path_without_ext, ext = os.path.splitext(file_path)
            file_name = os.path.basename(path_without_ext)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            folder_dest = f'{output_dir}/{file_name}'
            if not os.path.exists(folder_dest):
                os.makedirs(folder_dest)

            images = convert_from_path(file_path, 300)
            for idx, image in tqdm(enumerate(images)):
                image_path = f'./{folder_dest}/page-{idx}.png'
                image.save(image_path)


def image2markdown(input_dir, output_dir):
    # 遍历目录及其子目录中的所有文件
    files = os.listdir(input_dir)
    for file in tqdm(files):
        print(f"processsing {file}")
        file_path = os.path.join(input_dir, file)
        if os.path.isdir(file_path):
            png_files = os.listdir(file_path)
            for png_file in png_files:
                png_path = os.path.join(file_path, png_file)
                if png_path.endswith('.png'):
                    output_path = png_path.replace(input_dir, output_dir).replace('.png', '.md')
                    conent = convert2markdown(png_path)
                    output_sub_folder = file_path.replace(input_dir, output_dir)
                    if not os.path.exists(output_sub_folder):
                        os.makedirs(output_sub_folder)
                    with open(output_path, 'w') as file:
                        file.write(conent)   

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_path', type=str, default='./PDF', help='input path')
    parser.add_argument('--output_path', type=str, default='./output', help='output path')
    parser.add_argument('--region_name', type=str, default='us-west-2', help='aws region')
    args = parser.parse_args()
    pdf_path = args.input_path
    output_path = args.output_path
    region = args.region_name

    image_path = f"{output_path}/images"
    markdown_path = f"{output_path}/markdown"

    boto3_bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name=region
    )

    pdf2image(pdf_path, image_path)
    image2markdown(image_path, markdown_path)
