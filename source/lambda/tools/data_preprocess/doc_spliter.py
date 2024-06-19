import os
import re
import argparse
import json
import boto3
from bs4 import BeautifulSoup
from langchain.document_loaders import PDFMinerPDFasHTMLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import statistics

smr_client = boto3.client("sagemaker-runtime")
parameters = {
  "max_length": 2048,
  "temperature": 0.01,
  "num_beams": 1, # >1可能会报错，"probability tensor contains either `inf`, `nan` or element < 0"； 即使remove_invalid_values=True也不能解决
  "do_sample": False,
  "top_p": 0.7,
  "logits_processor" : None,
  # "remove_invalid_values" : True
}

'''
1. pip install pdfminer.six
'''
class Elembbox(object):
    left = -1
    top = -1
    width = -1 
    height = -1 
    right = -1 
    bottom = -1
    margin = 8 # for header text above table

    RAW_MAX_DIST = 120
    COL_MAX_DIST = 400

    # top 增加是往下 bottom > top
    # right 增加是往右 right > left

    def __init__(self, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.right = left + width
        self.bottom = top + height

    # def __str__(self):
    #     return "left:{}, top:{}, right:{}, bottom:{}, width:{}, height:{}".format(self.left, self.top, self.right, self.bottom, self.width, self.height)

    def __str__(self):
        return """<span style="position:absolute; border: red 1px solid; left:{}px; top:{}px; width:{}px; height:{}px;"></span>""".format(self.left, self.top, self.width, self.height)

    def is_overlap(self, other):
        if other is None:
            return False

        def is_pt_in_bbox(x, y, bbox):
            return x >= bbox.left \
                and x <= bbox.right \
                and y >= bbox.top - bbox.margin \
                and y <= bbox.bottom + bbox.margin
        
        lefttop_in = is_pt_in_bbox(other.left, other.top, self)
        leftbottom_in = is_pt_in_bbox(other.left, other.bottom, self)
        righttop_in = is_pt_in_bbox(other.right, other.top, self)
        rightbottom_in = is_pt_in_bbox(other.right, other.bottom, self)
        
        lefttop_in_2 = is_pt_in_bbox(self.left, self.top, other)
        leftbottom_in_2 = is_pt_in_bbox(self.left, self.bottom, other)
        righttop_in_2 = is_pt_in_bbox(self.right, self.top, other)
        rightbottom_in_2 = is_pt_in_bbox(self.right, self.bottom, other)

        return lefttop_in or leftbottom_in or righttop_in or rightbottom_in or lefttop_in_2 or leftbottom_in_2 or righttop_in_2 or rightbottom_in_2
    
    def is_beside(self, other):
        # only horizontal direction
        return self.is_overlap(other)

    def link_horizontal_lines(self, other):
        assert(self.height == 0)

        # merge the horizontal line
        if self.top == other.top:
            if self.left < other.left and other.left-1 <= self.right and other.right > self.right:
                # self.left < other.left <=self.right  < other.right
                return True, Elembbox(self.left, self.top, other.right - self.left, self.height)
            elif other.left < self.left and self.left-1 <= other.right and other.right < self.right:
                # other.left < self.left <=other.right  < self.right
                return True, Elembbox(other.left, self.top, self.right - other.left, self.height)

        return False, None

    def merge_horizontal_lines(self, other):
        if self.left == other.left and self.right == other.right:
            if other.top > self.bottom + self.RAW_MAX_DIST:
                return False, None 
            if self.bottom < other.top:
                return True, Elembbox(self.left, self.top, self.width, other.top - self.top)

        return False, None 

    def link_vertical_lines(self, other):
        assert(self.width == 0)

        # merge the vertical line
        if self.left == self.left:
            if self.top < other.top and other.top-1 <= self.bottom and self.bottom < other.bottom:
                # self.top < other.top <=self.bottom  < other.bottom
                return True, Elembbox(self.left, self.top, self.width, other.bottom - self.top)
            elif other.top < self.top and self.top-1 <= other.bottom and other.bottom < self.bottom:
                return True, Elembbox(self.left, other.top, self.width, self.bottom - other.top)

        return False, None        

    def merge_vertical_lines(self, other):
        if self.top == other.top and self.bottom == other.bottom:
            if other.right > self.right + self.COL_MAX_DIST:
                return False, None 
            if self.right < other.right:
                return True, Elembbox(self.left, self.top, other.right - self.left, self.height)

        return False, None 

def create_bbox_horizontal(origin_span):
    vertical_sorted_span = sorted(origin_span, key=lambda span_pos: (span_pos.top, span_pos.left))
    span_count = len(vertical_sorted_span)
    cur_span = vertical_sorted_span[0]
    merge_stage1_spans = []
    for idx in range(1, span_count):
        success, new_span = cur_span.link_horizontal_lines(vertical_sorted_span[idx])
        if not success:
            merge_stage1_spans.append(cur_span)
            cur_span = vertical_sorted_span[idx]
        else:
            cur_span = new_span

    merge_stage1_spans.append(cur_span)
    vertical_sorted_merge_spans = sorted(merge_stage1_spans, key=lambda span_pos: span_pos.left)
    # for item in vertical_sorted_merge_spans:
    #     print(item)

    # print('---------------')
    merge_stage2_spans = []
    cur_span = vertical_sorted_merge_spans[0]
    span_count = len(vertical_sorted_merge_spans)
    for idx in range(1, span_count):
        success, new_span = cur_span.merge_horizontal_lines(vertical_sorted_merge_spans[idx])
        if not success:
            merge_stage2_spans.append(cur_span)
            cur_span = vertical_sorted_merge_spans[idx]
        else:
            cur_span = new_span

    return [ item for item in merge_stage2_spans if item.height >0 ]

def create_bbox_vertical(origin_span):
    horizontal_sorted_span = sorted(origin_span, key=lambda span_pos: (span_pos.left, span_pos.top))
    span_count = len(horizontal_sorted_span)
    cur_span = horizontal_sorted_span[0]
    merge_stage1_spans = []
    for idx in range(1, span_count):
        success, new_span = cur_span.link_vertical_lines(horizontal_sorted_span[idx])
        if not success:
            merge_stage1_spans.append(cur_span)
            cur_span = horizontal_sorted_span[idx]
        else:
            cur_span = new_span

    merge_stage1_spans.append(cur_span)
    horizontal_sorted_merge_spans = sorted(merge_stage1_spans, key=lambda span_pos: span_pos.top)
    # for item in horizontal_sorted_merge_spans:
    #     print(item)

    # print('---------------')
    merge_stage2_spans = []
    cur_span = horizontal_sorted_merge_spans[0]
    span_count = len(horizontal_sorted_merge_spans)
    for idx in range(1, span_count):
        success, new_span = cur_span.merge_vertical_lines(horizontal_sorted_merge_spans[idx])
        if not success:
            merge_stage2_spans.append(cur_span)
            cur_span = horizontal_sorted_merge_spans[idx]
        else:
            cur_span = new_span

    return [ item for item in merge_stage2_spans if item.width >0 ]

def merge_bbox(bbox_a, bbox_b):
    top = min(bbox_a.top, bbox_b.top)
    left = min(bbox_a.left, bbox_b.left)
    right = max(bbox_a.right, bbox_b.right)
    bottom = max(bbox_a.bottom, bbox_b.bottom)
    width = right - left
    height = bottom - top

    return Elembbox(left, top, width, height)

def merge_bbox_list(bbox_list_a, bbox_list_b):
    if bbox_list_a is None:
        return bbox_list_b
    if bbox_list_b is None:
        return bbox_list_a

    merge_bbox_ret = []
    overlap_flag = [False] * len(bbox_list_b)
    for bbox_a in bbox_list_a:
        merge_box = bbox_a
        for idx, bbox_b in enumerate(bbox_list_b):
            if merge_box.is_overlap(bbox_b):
                overlap_flag[idx] = True
                merge_box = merge_bbox(merge_box, bbox_b)

        merge_bbox_ret.append(merge_box)

    for idx in range(len(bbox_list_b)):
        if overlap_flag[idx] == False:
            merge_bbox_ret.append(bbox_list_b[idx])

    return merge_bbox_ret

def find_all_table_bbox(pdf_path):
    loader = PDFMinerPDFasHTMLLoader(pdf_path)
    data = loader.load()[0]
    soup = BeautifulSoup(data.page_content,'html.parser')
    table_border = soup.find_all('span')
    h_span = []
    v_span = []
    font_size_list = []
    for idx, c in enumerate(table_border):
        # print("----{}---".format(idx))
        style_attribute = c.get('style')
        # 'position:absolute; border: gray 1px solid; left:0px; top:50px; width:612px; height:792px;'
        attr_list = [ p.split(':') for p in style_attribute.strip(";").split('; ')]
        span_pos = { k : int(v[:-2]) for k,v in attr_list if k in ['left', 'top', 'width', 'height', 'font-size']}
        keys = span_pos.keys()
        if 'font-size' in keys:
            font_size_list.append(span_pos['font-size'])

        if 'left' not in keys or 'top' not in keys or 'width' not in keys or 'height' not in keys:
            continue

        if span_pos['height'] == 0 and span_pos['width'] > 10:
            h_span.append(Elembbox(span_pos['left'],span_pos['top'],span_pos['width'],span_pos['height']))
        if span_pos['width'] == 0 and span_pos['height'] > 10:
            v_span.append(Elembbox(span_pos['left'],span_pos['top'],span_pos['width'],span_pos['height']))

    h_bbox_list = None
    if len(h_span) > 0:
        h_bbox_list = create_bbox_horizontal(h_span)
        # print("----h_span bbox----")
        # for item in h_bbox_list:
        #     print(item)

    v_bbox_list = None
    if len(v_span) > 0:        
        v_bbox_list = create_bbox_vertical(v_span)
        # print("----v_span bbox----")
        # for item in v_bbox_list:
        #     print(item)

    merge_bboxs =merge_bbox_list(h_bbox_list, v_bbox_list)
    # print("----merged bbox----")
    # for item in merge_bboxs:
    #     print(item)

    # update padding for Elembbox
    mode_font_size = statistics.mode(font_size_list)
    for i in range(len(merge_bboxs)):
        merge_bboxs[i].margin = mode_font_size

    return merge_bboxs

def fontsize_mapping(heading_fonts_arr):
    heading_fonts_set = list(set(heading_fonts_arr))
    heading_fonts_set.sort(reverse=True)
    idxs = range(len(heading_fonts_set))
    font_idx_mapping = dict(zip(heading_fonts_set,idxs))
    return font_idx_mapping

def split_pdf_to_snippet(pdf_path):
    loader = PDFMinerPDFasHTMLLoader(pdf_path)
    data = loader.load()[0]

    soup = BeautifulSoup(data.page_content,'html.parser')
    content = soup.find_all('div')

    cur_fs = None
    cur_text = None
    snippets = []   # first collect all snippets that have the same font size

    table_elem_bboxs = find_all_table_bbox(pdf_path)
    print("table bbox count: {}".format(len(table_elem_bboxs)))
    skip_count = 0

    def overlap_with_table(table_elem_bboxs, div_elem_bbox):
        for elem_bbox in table_elem_bboxs:
            if div_elem_bbox.is_overlap(elem_bbox):
                return True

        return False

    previous_div_bbox = None
    snippet_start = True
    snippet_follow = False
    snippet_state = snippet_start
    for c in content:
        div_style_attribute = c.get('style')
        attr_list = [ p.split(':') for p in div_style_attribute.strip(";").split('; ')]
        div_pos = { k : int(v[:-2]) for k,v in attr_list if k in ['left', 'top', 'width', 'height']}
        keys = div_pos.keys()
        if 'left' not in keys or 'top' not in keys or 'width' not in keys or 'height' not in keys:
            continue
        div_elem_bbox = Elembbox(div_pos['left'],div_pos['top'],div_pos['width'],div_pos['height'])
        
        if overlap_with_table(table_elem_bboxs, div_elem_bbox):
            skip_count += 1
            continue

        # if these two div is not beside each other 
        if not div_elem_bbox.is_beside(previous_div_bbox) and cur_text and cur_fs:
            snippets.append((cur_text,cur_fs,snippet_state))
            cur_fs = None
            cur_text = None
            snippet_state = snippet_start

        previous_div_bbox = div_elem_bbox

        sp_list = c.find_all('span')
        if not sp_list:
            continue

        for sp in sp_list:
            st = sp.get('style')
            if not st:
                continue
            fs = re.findall('font-size:(\d+)px',st)

            if not fs:
                continue
            fs = int(fs[0])

            if not cur_fs and not cur_text:
                cur_fs = fs
                cur_text = sp.text
                snippet_state = snippet_start
                continue

            if fs == cur_fs:
                cur_text += sp.text
            else:
                snippets.append((cur_text, cur_fs, snippet_state))
                snippet_state = snippet_start if fs > cur_fs else snippet_follow
                cur_fs = fs
                cur_text = sp.text
                
    snippets.append((cur_text,cur_fs, snippet_follow))
    
    # merge snippet
    merged_snippets = []
    temp_list = []
    doc_title = ''
    max_font_size = max([ item[1] for item in snippets])
    for snippet in snippets:
        if max_font_size == snippet[1]:
            doc_title = snippet[0]

        if len(temp_list) == 0 or snippet[2] == False:
            temp_list.append(snippet)
        else:
            content_list = [ item[0] for item in temp_list]
            font_size_list = [ item[1] for item in temp_list]
            content = "\n".join(content_list)
            font_size = max(font_size_list)
            temp_list.clear()
            temp_list.append(snippet)
            merged_snippets.append({"content":content, "font_size":font_size})

    print("filter {} table text".format(skip_count))
    return merged_snippets, doc_title

def split_pdf(pdf_path):
    semantic_snippets, doc_title = split_pdf_to_snippet(pdf_path)
    text_splitter = RecursiveCharacterTextSplitter( 
        chunk_size = 1024,
        chunk_overlap  = 0,
        separators=["\n\n", "\n", ".", "。", ",","，"," "], 
    )

    for item in semantic_snippets:
        content = item["content"]
        chunks = text_splitter.create_documents([ content ] )
        for chunk in chunks:
            snippet_info = {
                "content" : chunk.page_content,
                "font_size" : item["font_size"],
                "doc_title" : doc_title
            }
            yield snippet_info

def summarize(content, chunk_size = 512, llm_endpoint=""):
    summary = content
    if llm_endpoint and len(content) > chunk_size:
        # todo: call LLM to summarize
        prompt_template = """对下面反引号这段文档进行摘要，字数不超过{}

        ```
        {}
        ```
        摘要:
        """

        prompt = prompt_template.format(chunk_size, content[:1536])

        response_model = smr_client.invoke_endpoint(
            EndpointName=llm_endpoint,
            Body=json.dumps(
            {
                "inputs": prompt,
                "parameters": parameters,
                "history" : []
            }
            ),
            ContentType="application/json",
        )

        json_ret = json.loads(response_model['Body'].read().decode('utf8'))
        summary = json_ret['outputs']
    
    return summary

def convert_snippetJson2markdown(snippet_info, max_level=3):
    mk_head = ""
    p_head = ""
    for item in snippet_info["heading"][0:max_level][::-1]:
        mk_head += "#"
        head = "{} {}".format(mk_head, item["heading"].replace('\n',''))
        p_head += "{}\n".format(head)
    
    p_content = "{}\n{}".format(p_head, snippet_info['content'])

    return p_content

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file', type=str, default='./1.pdf', help='input file')
    parser.add_argument('--output_dir', type=str, default='./', help='output file')
    parser.add_argument('--sep', type=str, default='=====', help='separtor')
    parser.add_argument('--title_level', type=int, default=4, help='keep the tiltes of level')
    parser.add_argument('--chunk_size', type=int, default=128, help='chunk_size')
    parser.add_argument('--llm_endpoint', type=str, default="", help='llm_endpoint')
    args = parser.parse_args()
    pdf_path = args.input_file
    kg_dir = args.output_dir
    kg_name = os.path.basename(pdf_path).replace('.pdf','.json')
    separtor = args.sep
    max_title_level = args.title_level
    chunk_size = args.chunk_size
    llm_endpoint = args.llm_endpoint
    idx = 1

    f_name = "{}/{}".format(kg_dir, kg_name)
    out_f = open(f_name, 'w')
    snippet_arr = []
    for snippet_info in split_pdf(pdf_path):
        snippet_arr.append(snippet_info)
    all_info = json.dumps(snippet_arr, ensure_ascii=False)
    out_f.write(all_info)
    out_f.close()
    print("finish separation of {}".format(pdf_path))

