#!/usr/bin/env python
# coding: utf-8
import argparse
import json

def split_by(content, sep):
    return content.split(sep)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, help='input file')
    parser.add_argument('--output_file', type=str, help='output file')
    parser.add_argument('--doc_tile', type=str, default='', help='output file')
    parser.add_argument('--doc_category', type=str, default='', help='output file')

    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file
    doc_tile = args.doc_tile
    doc_category = args.doc_category

    outf = open(output_file, 'w')
    f = open(input_file, 'r')
    content = f.read()
    arr = split_by(content, '=====')

    json_arr = []
    for item in arr:
        question, answer = item.strip().split("\n", 1)
        question = question.replace("Question: ", "")
        answer = answer.replace("Answer: ", "")
        obj = {
            "Question":question, "Answer":answer
        }
        json_arr.append(obj)

    qa_content = {
        "doc_title" : doc_tile,
        "doc_category" : doc_category,
        "qa_list" : json_arr
    }

    json_content = json.dumps(qa_content, ensure_ascii=False)
    outf.write(json_content)
