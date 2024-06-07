import boto3
import json
import tiktoken
import argparse
from tqdm import tqdm

def get_token_num(tokenizer, input):
	tokens = tokenizer.encode(input)
	num_tokens = len(tokens)
	return num_tokens

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--input_file', type=str, default='./input.txt', help='Need pure text or markdown format')
	parser.add_argument('--output_file', type=str, default='./output.json', help='output file')
	args = parser.parse_args()
	input_file = args.input_file
	output_file = args.output_file

	tokenizer = tiktoken.get_encoding("cl100k_base")
	with open(input_file, 'r') as file:
		doc_content = file.read()
		# estimated_faq_num = int(get_token_num(tokenizer, doc_content) / 40)
		# print("estimated_faq_num:{}".format(estimated_faq_num))

		bedrock = boto3.client(service_name='bedrock-runtime', region_name="us-east-1")

		prompt_template1 ="""Human: 提取<document>文档中的Topic和Chapter Title. 提取的内容是json格式，其中Chapter Title是一个list.
<document>
{document}
</document>

Assistant:"""

		prompt = prompt_template1.format(document=doc_content)

		body = json.dumps({
		    "prompt": prompt,
		    "max_tokens_to_sample": 8000,
		    "temperature": 0.1,
		    "top_p": 0.9,
		    "stop_sequences": ["\n\nHuman:"]
		})

		modelId = 'anthropic.claude-v2'
		accept = 'application/json'
		contentType = 'application/json'

		response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
		response_body = json.loads(response.get('body').read())

		outline_info = response_body.get('completion')
		# print(outline_info)

		obj = json.loads(outline_info)

		prompt_template2="""Human: 基于<document>提供的文档，对于'CHAPTER'章节, 生成一组FAQ(Frequently Ask Question). 要求生成的问题和答案是以对话语气，格式为json并且以'Question'和'Answer'作为字段名，'Question'中仅仅包含问题本身，不要添加'根据文档内容'类似的话。
<document>
DOCUMENT
</document>

Assistant: 
[
{ "Question":
		"""

		qa_list = []
		topic = obj['Topic']
		for section_topic in tqdm(obj['Chapter Title']):
			prompt = prompt_template2.replace('CHAPTER', section_topic).replace('DOCUMENT',doc_content)
			body = json.dumps({
			    "prompt": prompt,
			    "max_tokens_to_sample": 8000,
			    "temperature": 0.1,
			    "top_p": 0.9,
			    "stop_sequences": ["\n\nHuman:"]
			})

			modelId = 'anthropic.claude-v2'
			accept = 'application/json'
			contentType = 'application/json'

			response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)

			response_body = json.loads(response.get('body').read())
			ret_str = '[{"Question":' + response_body.get('completion')
			ret_str = ret_str.replace('\n','')

			try:
				json_obj = json.loads(ret_str)
			except Exception as e:
				print("bad json format => {}".format(ret_str))
				continue

			qa_list.extend([{"page_content" : "{}=>{}".format(obj['Question'], obj['Answer']), "metadata" : {"content_type":"QA", "heading_hierachy" : [topic, section_topic]}} for obj in json_obj])

		qa_file_content = json.dumps(qa_list, ensure_ascii=False)

	output_file = open(output_file, 'w')
	output_file.write(qa_file_content)
