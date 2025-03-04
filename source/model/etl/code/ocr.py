import copy
import math
import time
import os

import numpy as np
import onnxruntime
from PIL import Image, ImageDraw
import cv2
from imaug import create_operators, transform
from postprocess import build_post_process
from gpu_config import get_provider_config
from model_config import MODEL_CONFIGS

provider, rec_batch_num, _ = get_provider_config()

class TextClassifier():
    def __init__(self):
        self.weights_path = os.path.join(os.environ['MODEL_PATH'], 'classifier.onnx')

        self.cls_image_shape = [3, 48, 192]
        self.cls_batch_num = 30
        self.cls_thresh = 0.9
        self.use_zero_copy_run = False
        postprocess_params = {
            'name': 'ClsPostProcess',
            "label_list": ['0', '180'],
        }
        self.postprocess_op = build_post_process(postprocess_params)

        self.ort_session = onnxruntime.InferenceSession(self.weights_path, providers=provider)

    def resize_norm_img(self, img):
        imgC, imgH, imgW = self.cls_image_shape
        h = img.shape[0]
        w = img.shape[1]
        ratio = w / float(h)
        if math.ceil(imgH * ratio) > imgW:
            resized_w = imgW
        else:
            resized_w = int(math.ceil(imgH * ratio))
        resized_image = np.array(Image.fromarray(img).resize((resized_w, imgH)))
        resized_image = resized_image.astype('float32')
        if self.cls_image_shape[0] == 1:
            resized_image = resized_image / 255
            resized_image = resized_image[np.newaxis, :]
        else:
            resized_image = resized_image.transpose((2, 0, 1)) / 255
        resized_image -= 0.5
        resized_image /= 0.5
        padding_im = np.zeros((imgC, imgH, imgW), dtype=np.float32)
        padding_im[:, :, 0:resized_w] = resized_image
        return padding_im

    def __call__(self, img_list):
        img_list = copy.deepcopy(img_list)
        img_num = len(img_list)
        # Calculate the aspect ratio of all text bars
        width_list = []
        for img in img_list:
            width_list.append(img.shape[1] / float(img.shape[0]))
        # Sorting can speed up the cls process
        indices = np.argsort(np.array(width_list))

        cls_res = [['', 0.0]] * img_num
        batch_num = self.cls_batch_num
        for beg_img_no in range(0, img_num, batch_num):
            end_img_no = min(img_num, beg_img_no + batch_num)
            norm_img_batch = []
            max_wh_ratio = 0
            for ino in range(beg_img_no, end_img_no):
                h, w = img_list[indices[ino]].shape[0:2]
                wh_ratio = w * 1.0 / h
                max_wh_ratio = max(max_wh_ratio, wh_ratio)
            for ino in range(beg_img_no, end_img_no):
                norm_img = self.resize_norm_img(img_list[indices[ino]])
                norm_img = norm_img[np.newaxis, :]
                norm_img_batch.append(norm_img)
            norm_img_batch = np.concatenate(norm_img_batch)
            norm_img_batch = norm_img_batch.copy()
            starttime = time.time()
            ort_inputs = {self.ort_session.get_inputs()[0].name: norm_img_batch}
            prob_out = self.ort_session.run(None, ort_inputs)[0]
            cls_result = self.postprocess_op(prob_out)
            for rno in range(len(cls_result)):
                label, score = cls_result[rno]
                cls_res[indices[beg_img_no + rno]] = [label, score]
                if '180' in label and score > self.cls_thresh:
                    img_list[indices[beg_img_no + rno]] = np.array(Image.fromarray(img_list[indices[beg_img_no + rno]]).transpose(Image.ROTATE_180))
        return img_list, cls_res

class TextDetector():
    def __init__(self, lang):
        model_config = MODEL_CONFIGS[lang]
        self.weights_path = os.path.join(os.environ['MODEL_PATH'], model_config['det'])

        self.det_algorithm = 'DB'
        self.use_zero_copy_run = False

        pre_process_list = [{'DetResizeForTest': {'limit_side_len': 1280, 'limit_type': 'max'}},
                            {'NormalizeImage': {'std': [0.229, 0.224, 0.225], 'mean': [0.485, 0.456, 0.406], 'scale': '1./255.', 'order': 'hwc'}},
                            {'ToCHWImage': None}, {'KeepKeys': {'keep_keys': ['image', 'shape']}}]
        pre_process_list_identity = [{'DetResizeForTest': {'identity': None}},
                            {'NormalizeImage': {'std': [0.229, 0.224, 0.225], 'mean': [0.485, 0.456, 0.406], 'scale': '1./255.', 'order': 'hwc'}},
                            {'ToCHWImage': None}, {'KeepKeys': {'keep_keys': ['image', 'shape']}}]
        postprocess_params = {'name': 'DBPostProcess', 'thresh': 0.1, 'box_thresh': 0.1, 'max_candidates': 1000, 'unclip_ratio': 1.5, 'use_dilation': False, 'score_mode': 'fast', 'box_type': 'quad'}
        self.preprocess_op = create_operators(pre_process_list)
        self.preprocess_op_identity = create_operators(pre_process_list_identity)
        self.postprocess_op = build_post_process(postprocess_params)
        self.ort_session = onnxruntime.InferenceSession(self.weights_path, providers=provider)
        _ = self.ort_session.run(None, {"x": np.zeros([1, 3, 64, 64], dtype='float32')})

    # load_pytorch_weights

    def order_points_clockwise(self, pts):
        """
        reference from: https://github.com/jrosebr1/imutils/blob/master/imutils/perspective.py
        # sort the points based on their x-coordinates
        """
        xSorted = pts[np.argsort(pts[:, 0]), :]

        # grab the left-most and right-most points from the sorted
        # x-roodinate points
        leftMost = xSorted[:2, :]
        rightMost = xSorted[2:, :]

        # now, sort the left-most coordinates according to their
        # y-coordinates so we can grab the top-left and bottom-left
        # points, respectively
        leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
        (tl, bl) = leftMost

        rightMost = rightMost[np.argsort(rightMost[:, 1]), :]
        (tr, br) = rightMost

        rect = np.array([tl, tr, br, bl], dtype="float32")
        return rect

    def clip_det_res(self, points, img_height, img_width):
        for pno in range(points.shape[0]):
            points[pno, 0] = int(min(max(points[pno, 0], 0), img_width - 1))
            points[pno, 1] = int(min(max(points[pno, 1], 0), img_height - 1))
        return points

    def filter_tag_det_res(self, dt_boxes, image_shape):
        img_height, img_width = image_shape[0:2]
        dt_boxes_new = []
        for box in dt_boxes:
            box = self.order_points_clockwise(box)
            box = self.clip_det_res(box, img_height, img_width)
            rect_width = int(np.linalg.norm(box[0] - box[1]))
            rect_height = int(np.linalg.norm(box[0] - box[3]))
            if rect_width <= 3 or rect_height <= 3:
                continue
            dt_boxes_new.append(box)
        dt_boxes = np.array(dt_boxes_new)
        return dt_boxes

    def filter_tag_det_res_only_clip(self, dt_boxes, image_shape):
        img_height, img_width = image_shape[0:2]
        dt_boxes_new = []
        for box in dt_boxes:
            box = self.clip_det_res(box, img_height, img_width)
            dt_boxes_new.append(box)
        dt_boxes = np.array(dt_boxes_new)
        return dt_boxes
    
    def __call__(self, img, scale=None):
        start = time.time()
        ori_im = img.copy()
        if scale:
            src_h, src_w, _ = img.shape
            resize_h = int(round(scale*src_h / 32) * 32)
            resize_w = int(round(scale*src_w / 32) * 32)
            img = cv2.resize(img, (resize_w, resize_h))
            data = {'image': img}
            data = transform(data, self.preprocess_op_identity)
            img, shape_list = data
            ratio_h = float(resize_h) / src_h
            ratio_w = float(resize_w) / src_w
            shape_list = np.array([src_h, src_w, ratio_h, ratio_w])
        else:
            data = {'image': img}
            data = transform(data, self.preprocess_op)
            img, shape_list = data
        if img is None:
            return None, 0
        img = np.expand_dims(img, axis=0)
        shape_list = np.expand_dims(shape_list, axis=0)
        img = img.copy()
        ort_inputs = {self.ort_session.get_inputs()[0].name: img}
        preds = {}
        preds['maps'] = self.ort_session.run(None, ort_inputs)[0]
        post_result = self.postprocess_op(preds, shape_list)
        dt_boxes = post_result[0]['points']
        dt_boxes = self.filter_tag_det_res(dt_boxes, ori_im.shape)
        return dt_boxes

class TextRecognizer():
    def __init__(self, lang='ch'):
        model_config = MODEL_CONFIGS[lang]
        self.weights_path = os.path.join(os.environ['MODEL_PATH'], model_config['rec'])

        postprocess_params = {
            'name': 'CTCLabelDecode',
            "character_type": model_config['character_type'],
            "character_dict_path": os.path.join(os.environ['MODEL_PATH'], model_config['dict_path']),
            "use_space_char": model_config['use_space_char']
        }

        self.limited_max_width = 1280
        self.limited_min_width = 16

        self.rec_image_shape = [3, 48, 480]
        self.rec_batch_num = rec_batch_num
        self.rec_algorithm = 'CRNN'
        self.use_zero_copy_run = False

        self.postprocess_op = build_post_process(postprocess_params)
        self.ort_session = onnxruntime.InferenceSession(self.weights_path, providers=provider)

    def resize_norm_img(self, img, max_wh_ratio):
        imgC, imgH, imgW = self.rec_image_shape

        assert imgC == img.shape[2]
        imgW = int((imgH * max_wh_ratio))
        # if self.use_onnx:
        #     w = self.input_tensor.shape[3:][0]
        #     if isinstance(w, str):
        #         pass
        #     elif w is not None and w > 0:
        #         imgW = w
        h, w = img.shape[:2]
        ratio = w / float(h)
        if math.ceil(imgH * ratio) > imgW:
            resized_w = imgW
        else:
            resized_w = int(math.ceil(imgH * ratio))
        resized_image = cv2.resize(img, (resized_w, imgH))
        resized_image = resized_image.astype('float32')
        resized_image = resized_image.transpose((2, 0, 1)) / 255
        resized_image -= 0.5
        resized_image /= 0.5
        padding_im = np.zeros((imgC, imgH, imgW), dtype=np.float32)
        padding_im[:, :, 0:resized_w] = resized_image
        return padding_im

    def __call__(self, img_list):
        img_num = len(img_list)
        # Calculate the aspect ratio of all text bars
        width_list = []
        for img in img_list:
            width_list.append(img.shape[1] / float(img.shape[0]))
        # Sorting can speed up the recognition process
        indices = np.argsort(np.array(width_list))

        # rec_res = []
        rec_res = [['', 0.0]] * img_num
        batch_num = self.rec_batch_num
        for beg_img_no in range(0, img_num, batch_num):
            end_img_no = min(img_num, beg_img_no + batch_num)
            norm_img_batch = []
            max_wh_ratio = 0
            for ino in range(beg_img_no, end_img_no):
                # h, w = img_list[ino].shape[0:2]
                h, w = img_list[indices[ino]].shape[0:2]
                wh_ratio = w * 1.0 / h
                max_wh_ratio = max(max_wh_ratio, wh_ratio)
            max_wh_ratio = math.ceil(max_wh_ratio)
            for ino in range(beg_img_no, end_img_no):
                # norm_img = self.resize_norm_img(img_list[ino], max_wh_ratio)
                norm_img = self.resize_norm_img(img_list[indices[ino]],
                                                max_wh_ratio)
                norm_img = norm_img[np.newaxis, :]
                norm_img_batch.append(norm_img)
            norm_img_batch = np.concatenate(norm_img_batch)
            norm_img_batch = norm_img_batch.copy()
            norm_img_batch = np.ascontiguousarray(norm_img_batch)
            ort_inputs = {self.ort_session.get_inputs()[0].name: norm_img_batch}
            start = time.time()
            preds = self.ort_session.run(None, ort_inputs)[0]
            rec_result = self.postprocess_op(preds)
            for rno in range(len(rec_result)):
                rec_res[indices[beg_img_no + rno]] = rec_result[rno]
        return rec_res
def sorted_boxes(dt_boxes):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """
    num_boxes = dt_boxes.shape[0]
    sorted_boxes = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))
    _boxes = list(sorted_boxes)

    for i in range(num_boxes - 1):
        if abs(_boxes[i + 1][0][1] - _boxes[i][0][1]) < 10 and (
            _boxes[i + 1][0][0] < _boxes[i][0][0]
        ):
            tmp = _boxes[i]
            _boxes[i] = _boxes[i + 1]
            _boxes[i + 1] = tmp
    return _boxes
class TextSystem:
    def __init__(self):
        #self.text_detector = TextDetector()
        self.text_detector = {
            'ch': TextDetector('ch'),
            'en': TextDetector('en'),
            'multi': TextDetector('multi'),
        }
        self.text_recognizer = {
            'ch': TextRecognizer('ch'),
            'en': TextRecognizer('en'),
            'multi': TextRecognizer('multi'),
        }
        
        self.drop_score = 0.4
        #self.text_classifier = TextClassifier()

    def get_rotate_crop_image(self, img, points):
        """
        img_height, img_width = img.shape[0:2]
        left = int(np.min(points[:, 0]))
        right = int(np.max(points[:, 0]))
        top = int(np.min(points[:, 1]))
        bottom = int(np.max(points[:, 1]))
        img_crop = img[top:bottom, left:right, :].copy()
        points[:, 0] = points[:, 0] - left
        points[:, 1] = points[:, 1] - top
        """
        img_crop_width = int(
            max(
                np.linalg.norm(points[0] - points[1]),
                np.linalg.norm(points[2] - points[3]),
            )
        )
        img_crop_height = int(
            max(
                np.linalg.norm(points[0] - points[3]),
                np.linalg.norm(points[1] - points[2]),
            )
        )
        pts_std = np.float32(
            [
                [0, 0],
                [img_crop_width, 0],
                [img_crop_width, img_crop_height],
                [0, img_crop_height],
            ]
        )
        M = cv2.getPerspectiveTransform(points, pts_std)
        dst_img = cv2.warpPerspective(
            img,
            M,
            (img_crop_width, img_crop_height),
            borderMode=cv2.BORDER_REPLICATE,
            flags=cv2.INTER_CUBIC,
        )
        dst_img_height, dst_img_width = dst_img.shape[0:2]
        if dst_img_height * 1.0 / dst_img_width >= 1.5:
            dst_img = np.rot90(dst_img)
        return dst_img

    def __call__(self, img, lang='ch', scale=None):
        ori_im = img.copy()
        
        dt_boxes = self.text_detector[lang](img, scale)
        
        if dt_boxes is None:
            return None, None
        img_crop_list = []

        dt_boxes = sorted_boxes(dt_boxes)

        for bno in range(len(dt_boxes)):
            tmp_box = copy.deepcopy(dt_boxes[bno])
            img_crop = self.get_rotate_crop_image(ori_im, tmp_box)
            img_crop_list.append(img_crop)
        #img_crop_list, angle_list = self.text_classifier(img_crop_list)

        rec_res = self.text_recognizer[lang](img_crop_list)
        filter_boxes, filter_rec_res = [], []
        for box, rec_reuslt in zip(dt_boxes, rec_res):
            text, score = rec_reuslt
            if score >= self.drop_score:
                filter_boxes.append(box)
                filter_rec_res.append(rec_reuslt)
        return filter_boxes, filter_rec_res