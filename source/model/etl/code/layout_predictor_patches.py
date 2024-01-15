# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys
import cv2
import numpy as np
import time

from utils import preprocess, multiclass_nms, postprocess
import onnxruntime

class LayoutPredictor(object):
    def __init__(self, layout_model_dir):
        self.ort_session = onnxruntime.InferenceSession(os.path.join(layout_model_dir, 'yolox_l_mix.onnx'), providers=['CUDAExecutionProvider'])
        print(self.ort_session)
        self.categorys = ['text', 'title', 'figure', 'table']
    def __call__(self, img):
        ori_im = img.copy()

        starttime = time.time()

        h,w,_ = img.shape
        h_ori, w_ori, _ = img.shape
        h, w = (640, 640)
        image, ratio = preprocess(img, (h, w))
        res = self.ort_session.run(['output'], {'images': image[np.newaxis,:]})[0]
        predictions = postprocess(res, (h, w), p6=False)[0]
        boxes = predictions[:, :4]
        
        scores = predictions[:, 4, None] * predictions[:, 5:]
        
        boxes_xyxy = np.ones_like(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2]/2.
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3]/2.
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2]/2.
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3]/2.
        boxes_xyxy /= ratio
        
        dets = multiclass_nms(boxes_xyxy, scores, nms_thr=0.15, score_thr=0.3)
        if dets is None:
            return [], time.time() - starttime
        scores = dets[:, 4]
        final_cls_inds = dets[:, 5]
        final_boxes = dets[:, :4]#.astype('int')
        result = []
        for box_idx,box in enumerate(final_boxes):
            result.append({'label': self.categorys[int(final_cls_inds[box_idx])],
                           'bbox': box})
        elapse = time.time() - starttime
        return result, elapse