import os
import re
import argparse
import openai
import json
from tqdm import tqdm
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import MarkdownTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

# you need to install these packages: pypdf, tqdm, openai, langchain 

# Please execute => export OPENAI_API_KEY={key}
openai.api_key = os.getenv("OPENAI_API_KEY")


en_prompt_template = """
Here is one page of {product}'s manual document
```
{page}
```
Please automatically generate as many questions as possible based on this manual document, and follow these rules:
1. "{product}"" should be contained in every question
2. questions start with "Question:"
3. answers begin with "Answer:"
"""

# zh_prompt_template = """
# Here is one page of {product}'s manual document
# ```
# {page}
# ```
# Please automatically generate as many questions as possible based on this manual document, and follow these rules:
# 1. "{product}"" should be contained in every question
# 2. questions start with "Question:"
# 3. answers begin with "Answer:"
# 4. Answer in Chinese
# """

zh_prompt_template = """
如下三个反括号中是{product}的产品文档片段
```
{page}
```
请基于这些文档片段自动生成尽可能多的问题以及对应答案, 尽可能详细全面, 并且遵循如下规则:
1. "{product}"需要一直被包含在Question中
2. 问题部分需要以"Question:"开始
3. 答案部分需要以"Answer:"开始
"""

def Generate_QA(prompt):
    messages = [{"role": "user", "content": f"{prompt}"}]
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=messages,
      temperature=0,
      max_tokens=2048
    )
    
    content = response.choices[0]["message"]["content"]
    arr = content.split('Question:')[1:]
    qa_pair = [ p.split('Answer:') for p in arr ]
    return qa_pair


def Generate_QA_From_Docs(pages, prompt_template, product_name="Midea Dishwasher", out_format="json"):
    for page in tqdm(pages[13:23]):
        # print(page)
        # yield { "doc" : page.page_content }
        prompt = prompt_template.format(product=product_name, page=page.page_content)
        qa_list = Generate_QA(prompt)
        for q_c,a_c in qa_list:
            if out_format == "json":
                ret = page.metadata
                ret["Q"] = q_c.strip()
                ret["A"] = a_c.strip()
                yield ret
            elif out_format == "QA":
                yield "Question: " + q_c.strip() + "\nAnswer: " + a_c.strip() + "\n\n"
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, default='./1-Manual.pdf', help='input file')
    parser.add_argument('--output_file', type=str, default='./FAQ.txt', help='output file')
    parser.add_argument('--product', type=str, default="Midea Dishwasher", help='specify the product name of doc')
    parser.add_argument('--input_format', type=str, default="pdf", help='specify the format')
    parser.add_argument('--lang', type=str, default="en", help='specify the language')
    parser.add_argument('--output_format', type=str, default="json", help='specify the language')
    args = parser.parse_args()
    doc_path = args.input_file
    product_name = args.product
    qa_path = args.output_file
    in_format = args.input_format
    lang = args.lang
    out_format= args.output_format

    prompt_template = zh_prompt_template if lang == "zh" else en_prompt_template

    docs = None
    if in_format == "pdf":
        loader = PyPDFLoader(doc_path)
        docs = loader.load_and_split()
    elif in_format == "md":
        in_file = open(doc_path, 'r')
        markdown_text = in_file.read()
        # markdown_splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=0)
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["#","\n\n", "\n"], 
            chunk_size = 1000,
            chunk_overlap  = 0
        )
        docs = text_splitter.create_documents([markdown_text])
    else:
        raise RuntimeError
    
    out_f = open(qa_path, 'w')
    with open(qa_path, 'w') as out_f:
        for result in Generate_QA_From_Docs(docs, prompt_template, product_name, out_format):
            if out_format == "json":
                out_f.write(json.dumps(result, ensure_ascii=False))
                out_f.write("\n")
            elif out_format == "QA":
                out_f.write(result)

