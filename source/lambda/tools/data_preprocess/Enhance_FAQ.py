import os
import re
import argparse
import openai
import json
from tqdm import tqdm
import tiktoken
import math
# you need to install these packages: pypdf, tqdm, openai, langchain 

# Please excute => export OPENAI_API_KEY={key}
openai.api_key = os.getenv("OPENAI_API_KEY")
tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

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
如下三个反引号中是{product}的相关知识信息, 请基于这部分知识信息自动生成{question_num}个问题以及对应答案
```
{knowledge}
```
要求尽可能详细全面, 并且遵循如下规则:
1. 生成的内容不要超出反引号中信息的范围
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


def Generate_QA_From_Docs(qa_list, prompt_template, product_name="Midea Dishwasher", out_format="json"):
    for qa_pair in tqdm(qa_list):
        tokens = tokenizer.encode(qa_pair)
        token_cnt = len(tokens)
        q_num =  math.ceil(token_cnt/40)
        
        origin_q = qa_pair.split('Answer: ')[0].replace("Question: ", "")
        origin_a = qa_pair.split('Answer: ')[1]
        prompt = prompt_template.format(product=product_name, knowledge=qa_pair, question_num=q_num)
        qa_list = []
        try:
            qa_list = Generate_QA(prompt)
        except Exception as e:
            print(e)

        for gen_qa in qa_list:
            if len(gen_qa) != 2:
                continue
            q_c, a_c = gen_qa
            obj = { "origin_question":origin_q, "origin_answer":origin_a, "generate_question" : q_c.strip(), "generate_answer" : a_c.strip() }
            yield obj
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, default='./all.faq', help='input file')
    parser.add_argument('--output_file', type=str, default='./output.json', help='output file')
    parser.add_argument('--product', type=str, default="《海岛奇兵》游戏", help='specify the product name of doc')
    args = parser.parse_args()
    doc_path = args.input_file
    product_name = args.product
    qa_path = args.output_file
    out_format = 'json'
    lang = 'zh'

    prompt_template = zh_prompt_template if lang == "zh" else en_prompt_template

    docs = None
    
    out_f = open(qa_path, 'w')
    with open(doc_path, 'r') as input_f:
        content = input_f.read()
        knowledges = content.split("=====")
        # for idx, item in enumerate(knowledges):
        #     if item.startswith("Question: 定时器"):
        #         import pdb
        #         pdb.set_trace()
        #     else:
        #         continue
        for idx, result in enumerate(Generate_QA_From_Docs(knowledges, prompt_template, product_name, out_format)):
            print(f"writing {idx}-th qa pair...")
            if out_format == "json":
                out_f.write(json.dumps(result, ensure_ascii=False))
                out_f.write("\n")
            elif out_format == "QA":
                out_f.write(result)

