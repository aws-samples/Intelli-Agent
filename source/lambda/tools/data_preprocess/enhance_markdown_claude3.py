import os
import boto3
import pandas as pd
import json
from io import StringIO
import pandas as pd
import argparse
from tqdm import tqdm
from langchain.text_splitter import MarkdownTextSplitter

def construct_gen_summary_prompt(content):
    prompt = f"""Please give a summary for below content.
    <content>
    {content}
    <content>

    Please skip the preamble, go straight into the answer. Put the answer in <summary>
    """

    messages = [ {"role":"user", "content": prompt}, {"role":"assistant", "content" : "\n<summary>"}]

    input_body = {}
    input_body["anthropic_version"] = "bedrock-2023-05-31"
    input_body["messages"] = messages
    input_body["max_tokens"] = 1024
    input_body["stop_sequences"] = ['</summary>']

    body = json.dumps(input_body)

    return body

def construct_QA_list_prompt(content, NUMBER=5):
    PERSPECTIVE = "FAQ Organizer"
    examples = """[{"Question": "Q1", "Answer": "A1"}, {"Question": "Q2", "Answer": "A2"}, ...]"""

    prompt = f"""Utilize Natural Language Processing techniques and Generative AI to create new Question/Answer pair textual training data for OpenAI LLMs by drawing inspiration from the given seed content: <content>{content}</content> 

Here are the steps to follow:

1. Examine the provided seed content to identify significant and important topics, entities, relationships, and themes. You should use each important topic, entity, relationship, and theme you recognize. You can employ methods such as named entity recognition, content summarization, keyword/keyphrase extraction, and semantic analysis to comprehend the content deeply.

2. Based on the analysis conducted in the first step, employ a generative language model to generate fresh, new synthetic text samples. These samples should cover the same topic, entities, relationships, and themes present in the seed data. Aim to generate {NUMBER} high-quality variations that accurately explore different Question and Answer possibilities within the data space.

3. Ensure that the generated synthetic samples exhibit language diversity. Vary elements like wording, sentence structure, tone, and complexity while retaining the core concepts. The objective is to produce diverse, representative data rather than repetitive instances.

4. Format and deliver the generated synthetic samples in a structured Pandas Dataframe suitable for training and machine learning purposes.

5. The desired output length is roughly equivalent to the length of the seed content.

Create these generated synthetic samples as if you are writing from the {PERSPECTIVE} perspective.

Do not include any commentary or extraneous casualties.

Only output the resulting dataframe in the format of this example:  <output>{examples}</output>

"""

    messages = [ 
        {"role":"user", "content" : prompt },
        {"role":"assistant", "content": "<output>"}
    ]

    input_body = {}
    input_body["anthropic_version"] = "bedrock-2023-05-31"
    input_body["messages"] = messages
    input_body["system"] = "You are a AI Assistant."
    input_body["max_tokens"] = 2048
    input_body["stop_sequences"] = ['</output>']

    body = json.dumps(input_body)

    return body

def markdown_spliter(file_content):
    md_splitter = MarkdownTextSplitter( 
        chunk_size = 2048,
        chunk_overlap  = 0,
    )
    
    results = []
    chunks = md_splitter.create_documents([ file_content ] )
    for chunk in chunks:
        results.append(chunk.page_content)

    return results

def call_bedrock_enhance(content, prompt_func):
    request_body = prompt_func(content)
    request_options = {
        "body": request_body,
        "modelId": 'anthropic.claude-3-sonnet-20240229-v1:0',
        "accept": "application/json",
        "contentType": "application/json",
    }

    response = boto3_bedrock.invoke_model(**request_options)

    body = response.get('body').read().decode('utf-8')

    body_dict = json.loads(body)

    summary = body_dict['content'][0].get("text")

    return summary

def enhance_markdown(content):
    try:
        enhanced_data = []

        if len(content) < 2048:
            enhanced_data.append([content, content, 'NoQA'])
        else:
            paragraphs = markdown_spliter(content)
            enhanced_data = [ [p, content, 'NoQA'] for p in paragraphs ]
            
        summary = call_bedrock_enhance(content, construct_gen_summary_prompt)
        enhanced_data.append([summary, content, 'NoQA'])

        qa_list_str = call_bedrock_enhance(content, construct_QA_list_prompt)
        obj_list = json.loads(qa_list_str)
        qa_list = [ [ item['Question'], content, 'NoQA' ] for item in obj_list ]
        enhanced_data.extend(qa_list)

        df = pd.DataFrame(enhanced_data, columns=['Trigger', 'Content', 'doc_type'])

        return df
    except Exception as e:
        print(str(e))
  
    return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', type=str, default='106839800180-24-02-07-02-51-47-bucket', help='input bucket')
    parser.add_argument('--prefix', type=str, default='mihoyo-poc/enhanced_test/', help='input bucket')
    parser.add_argument('--input_path', type=str, default='', help='input path')
    parser.add_argument('--output_path', type=str, default='./output', help='output path')
    parser.add_argument('--region_name', type=str, default='us-west-2', help='aws region')
    args = parser.parse_args()

    input_path = args.input_path
    output_path = args.output_path
    region = args.region_name
    bucket_name = args.bucket
    prefix = args.prefix

    boto3_bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name=region
    )

    df = None
    content = None
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    if input_path and os.path.exists(input_path):
        for root, dirs, files in os.walk(input_path):
            md_files = [ file for file in files if file.endswith('.md')]
            for filename in tqdm(md_files):
                f_path = os.path.join(root, filename)

                print(f"processing file: {f_path}")
                with open(f_path, 'r') as f:
                    content = f.read()

                df = enhance_markdown(content)      
                if df is not None:
                    output_filename = "{}__{}".format(os.path.basename(root), filename.replace('.md', '.xlsx'))
                    print(output_filename)
                    df.to_excel(f'{output_path}/{output_filename}.xlsx', index=False)
    else:      
        s3 = boto3.client('s3')
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        text_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.md')]

        for file in tqdm(text_files):
            output_filename = '__'.join(file.split('/')[2:])
            print(f"processing file: {file}")
            obj = s3.get_object(Bucket=bucket_name, Key=file)
            content = obj['Body'].read().decode('utf-8')
            df = enhance_markdown(content)      
            if df is not None:
                df.to_excel(f'{output_path}/{output_filename}.xlsx', index=False)
