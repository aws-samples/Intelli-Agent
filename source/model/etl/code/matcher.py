# copyright (c) 2022 PaddlePaddle Authors. All Rights Reserve.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
def deal_bb(result_token):
    """
    In our opinion, <b></b> always occurs in <thead></thead> text's context.
    This function will find out all tokens in <thead></thead> and insert <b></b> by manual.
    :param result_token:
    :return:
    """
    # find out <thead></thead> parts.
    thead_pattern = '<thead>(.*?)</thead>'
    if re.search(thead_pattern, result_token) is None:
        return result_token
    thead_part = re.search(thead_pattern, result_token).group()
    origin_thead_part = copy.deepcopy(thead_part)

    # check "rowspan" or "colspan" occur in <thead></thead> parts or not .
    span_pattern = "<td rowspan=\"(\d)+\" colspan=\"(\d)+\">|<td colspan=\"(\d)+\" rowspan=\"(\d)+\">|<td rowspan=\"(\d)+\">|<td colspan=\"(\d)+\">"
    span_iter = re.finditer(span_pattern, thead_part)
    span_list = [s.group() for s in span_iter]
    has_span_in_head = True if len(span_list) > 0 else False

    if not has_span_in_head:
        # <thead></thead> not include "rowspan" or "colspan" branch 1.
        # 1. replace <td> to <td><b>, and </td> to </b></td>
        # 2. it is possible to predict text include <b> or </b> by Text-line recognition,
        #    so we replace <b><b> to <b>, and </b></b> to </b>
        thead_part = thead_part.replace('<td>', '<td><b>')\
            .replace('</td>', '</b></td>')\
            .replace('<b><b>', '<b>')\
            .replace('</b></b>', '</b>')
    else:
        # <thead></thead> include "rowspan" or "colspan" branch 2.
        # Firstly, we deal rowspan or colspan cases.
        # 1. replace > to ><b>
        # 2. replace </td> to </b></td>
        # 3. it is possible to predict text include <b> or </b> by Text-line recognition,
        #    so we replace <b><b> to <b>, and </b><b> to </b>

        # Secondly, deal ordinary cases like branch 1

        # replace ">" to "<b>"
        replaced_span_list = []
        for sp in span_list:
            replaced_span_list.append(sp.replace('>', '><b>'))
        for sp, rsp in zip(span_list, replaced_span_list):
            thead_part = thead_part.replace(sp, rsp)

        # replace "</td>" to "</b></td>"
        thead_part = thead_part.replace('</td>', '</b></td>')

        # remove duplicated <b> by re.sub
        mb_pattern = "(<b>)+"
        single_b_string = "<b>"
        thead_part = re.sub(mb_pattern, single_b_string, thead_part)

        mgb_pattern = "(</b>)+"
        single_gb_string = "</b>"
        thead_part = re.sub(mgb_pattern, single_gb_string, thead_part)

        # ordinary cases like branch 1
        thead_part = thead_part.replace('<td>', '<td><b>').replace('<b><b>',
                                                                   '<b>')

    # convert <tb><b></b></tb> back to <tb></tb>, empty cell has no <b></b>.
    # but space cell(<tb> </tb>)  is suitable for <td><b> </b></td>
    thead_part = thead_part.replace('<td><b></b></td>', '<td></td>')
    # deal with duplicated <b></b>
    thead_part = deal_duplicate_bb(thead_part)
    # deal with isolate span tokens, which causes by wrong predict by structure prediction.
    # eg.PMC5994107_011_00.png
    thead_part = deal_isolate_span(thead_part)
    # replace original result with new thead part.
    result_token = result_token.replace(origin_thead_part, thead_part)
    return result_token
def deal_eb_token(master_token):
    """
    post process with <eb></eb>, <eb1></eb1>, ...
    emptyBboxTokenDict = {
        "[]": '<eb></eb>',
        "[' ']": '<eb1></eb1>',
        "['<b>', ' ', '</b>']": '<eb2></eb2>',
        "['\\u2028', '\\u2028']": '<eb3></eb3>',
        "['<sup>', ' ', '</sup>']": '<eb4></eb4>',
        "['<b>', '</b>']": '<eb5></eb5>',
        "['<i>', ' ', '</i>']": '<eb6></eb6>',
        "['<b>', '<i>', '</i>', '</b>']": '<eb7></eb7>',
        "['<b>', '<i>', ' ', '</i>', '</b>']": '<eb8></eb8>',
        "['<i>', '</i>']": '<eb9></eb9>',
        "['<b>', ' ', '\\u2028', ' ', '\\u2028', ' ', '</b>']": '<eb10></eb10>',
    }
    :param master_token:
    :return:
    """
    master_token = master_token.replace('<eb></eb>', '<td></td>')
    master_token = master_token.replace('<eb1></eb1>', '<td> </td>')
    master_token = master_token.replace('<eb2></eb2>', '<td><b> </b></td>')
    master_token = master_token.replace('<eb3></eb3>', '<td>\u2028\u2028</td>')
    master_token = master_token.replace('<eb4></eb4>', '<td><sup> </sup></td>')
    master_token = master_token.replace('<eb5></eb5>', '<td><b></b></td>')
    master_token = master_token.replace('<eb6></eb6>', '<td><i> </i></td>')
    master_token = master_token.replace('<eb7></eb7>',
                                        '<td><b><i></i></b></td>')
    master_token = master_token.replace('<eb8></eb8>',
                                        '<td><b><i> </i></b></td>')
    master_token = master_token.replace('<eb9></eb9>', '<td><i></i></td>')
    master_token = master_token.replace('<eb10></eb10>',
                                        '<td><b> \u2028 \u2028 </b></td>')
    return master_token


def distance(box_1, box_2):
    x1, y1, x2, y2 = box_1
    x3, y3, x4, y4 = box_2
    dis = abs(x3 - x1) + abs(y3 - y1) + abs(x4 - x2) + abs(y4 - y2)
    dis_2 = abs(x3 - x1) + abs(y3 - y1)
    dis_3 = abs(x4 - x2) + abs(y4 - y2)
    return dis + min(dis_2, dis_3)


def compute_iou(rec1, rec2):
    """
    computing IoU
    :param rec1: (y0, x0, y1, x1), which reflects
            (top, left, bottom, right)
    :param rec2: (y0, x0, y1, x1)
    :return: scala value of IoU
    """
    # computing area of each rectangles
    S_rec1 = (rec1[2] - rec1[0]) * (rec1[3] - rec1[1])
    S_rec2 = (rec2[2] - rec2[0]) * (rec2[3] - rec2[1])

    # computing the sum_area
    sum_area = S_rec1 + S_rec2

    # find the each edge of intersect rectangle
    left_line = max(rec1[1], rec2[1])
    right_line = min(rec1[3], rec2[3])
    top_line = max(rec1[0], rec2[0])
    bottom_line = min(rec1[2], rec2[2])

    # judge if there is an intersect
    if left_line >= right_line or top_line >= bottom_line:
        return 0.0
    else:
        intersect = (right_line - left_line) * (bottom_line - top_line)
        return (intersect / (sum_area - intersect)) * 1.0


class TableMatch:
    def __init__(self, filter_ocr_result=False, use_master=False):
        self.filter_ocr_result = filter_ocr_result
        self.use_master = use_master

    def __call__(self, structure_res, dt_boxes, rec_res):
        pred_structures, pred_bboxes = structure_res
        if self.filter_ocr_result:
            dt_boxes, rec_res = self._filter_ocr_result(pred_bboxes, dt_boxes,
                                                        rec_res)
        matched_index = self.match_result(dt_boxes, pred_bboxes)
        if self.use_master:
            pred_html, pred = self.get_pred_html_master(pred_structures,
                                                        matched_index, rec_res)
        else:
            pred_html, pred = self.get_pred_html(pred_structures, matched_index,
                                                 rec_res)
        return pred_html

    def match_result(self, dt_boxes, pred_bboxes):
        matched = {}
        for i, gt_box in enumerate(dt_boxes):
            distances = []
            for j, pred_box in enumerate(pred_bboxes):
                if len(pred_box) == 8:
                    pred_box = [
                        np.min(pred_box[0::2]), np.min(pred_box[1::2]),
                        np.max(pred_box[0::2]), np.max(pred_box[1::2])
                    ]
                distances.append((distance(gt_box, pred_box),
                                  1. - compute_iou(gt_box, pred_box)
                                  ))  # compute iou and l1 distance
            sorted_distances = distances.copy()
            # select det box by iou and l1 distance
            sorted_distances = sorted(
                sorted_distances, key=lambda item: (item[1], item[0]))
            if distances.index(sorted_distances[0]) not in matched.keys():
                matched[distances.index(sorted_distances[0])] = [i]
            else:
                matched[distances.index(sorted_distances[0])].append(i)
        return matched

    def get_pred_html(self, pred_structures, matched_index, ocr_contents):
        end_html = []
        td_index = 0
        for tag in pred_structures:
            if '</td>' in tag:
                if '<td></td>' == tag:
                    end_html.extend('<td>')
                if td_index in matched_index.keys():
                    b_with = False
                    if '<b>' in ocr_contents[matched_index[td_index][
                            0]] and len(matched_index[td_index]) > 1:
                        b_with = True
                        end_html.extend('<b>')
                    for i, td_index_index in enumerate(matched_index[td_index]):
                        content = ocr_contents[td_index_index][0]
                        if len(matched_index[td_index]) > 1:
                            if len(content) == 0:
                                continue
                            if content[0] == ' ':
                                content = content[1:]
                            if '<b>' in content:
                                content = content[3:]
                            if '</b>' in content:
                                content = content[:-4]
                            if len(content) == 0:
                                continue
                            if i != len(matched_index[
                                    td_index]) - 1 and ' ' != content[-1]:
                                content += ' '
                        end_html.extend(content)
                    if b_with:
                        end_html.extend('</b>')
                if '<td></td>' == tag:
                    end_html.append('</td>')
                else:
                    end_html.append(tag)
                td_index += 1
            else:
                end_html.append(tag)
        return ''.join(end_html), end_html

    def get_pred_html_master(self, pred_structures, matched_index,
                             ocr_contents):
        end_html = []
        td_index = 0
        for token in pred_structures:
            if '</td>' in token:
                txt = ''
                b_with = False
                if td_index in matched_index.keys():
                    if '<b>' in ocr_contents[matched_index[td_index][
                            0]] and len(matched_index[td_index]) > 1:
                        b_with = True
                    for i, td_index_index in enumerate(matched_index[td_index]):
                        content = ocr_contents[td_index_index][0]
                        if len(matched_index[td_index]) > 1:
                            if len(content) == 0:
                                continue
                            if content[0] == ' ':
                                content = content[1:]
                            if '<b>' in content:
                                content = content[3:]
                            if '</b>' in content:
                                content = content[:-4]
                            if len(content) == 0:
                                continue
                            if i != len(matched_index[
                                    td_index]) - 1 and ' ' != content[-1]:
                                content += ' '
                        txt += content
                if b_with:
                    txt = '<b>{}</b>'.format(txt)
                if '<td></td>' == token:
                    token = '<td>{}</td>'.format(txt)
                else:
                    token = '{}</td>'.format(txt)
                td_index += 1
            token = deal_eb_token(token)
            end_html.append(token)
        html = ''.join(end_html)
        html = deal_bb(html)
        return html, end_html

    def _filter_ocr_result(self, pred_bboxes, dt_boxes, rec_res):
        y1 = pred_bboxes[:, 1::2].min()
        new_dt_boxes = []
        new_rec_res = []

        for box, rec in zip(dt_boxes, rec_res):
            if np.max(box[1::2]) < y1:
                continue
            new_dt_boxes.append(box)
            new_rec_res.append(rec)
        return new_dt_boxes, new_rec_res
