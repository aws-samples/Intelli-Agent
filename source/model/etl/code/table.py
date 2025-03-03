from imaug import create_operators
from postprocess import build_post_process
from matcher import TableMatch
import time
import copy
from imaug import create_operators, transform
import numpy as np
import os
import onnxruntime as ort
from model_config import TABLE_CONFIG

def get_session_options():
    sess_options = ort.SessionOptions()
    config = TABLE_CONFIG['model']['session_options']
    sess_options.intra_op_num_threads = config['intra_op_num_threads']
    sess_options.execution_mode = getattr(ort.ExecutionMode, config['execution_mode'])
    sess_options.graph_optimization_level = getattr(ort.GraphOptimizationLevel, config['optimization_level'])
    return sess_options

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

class TableStructurer(object):
    def __init__(self):
        self.use_onnx = True
        self.preprocess_op = create_operators(TABLE_CONFIG['preprocess'])
        
        postprocess_params = dict(TABLE_CONFIG['postprocess'])
        postprocess_params['character_dict_path'] = os.path.join(os.environ['MODEL_PATH'], postprocess_params.pop('dict_path'))
        self.postprocess_op = build_post_process(postprocess_params)
        
        sess = ort.InferenceSession(
            os.path.join(os.environ['MODEL_PATH'], TABLE_CONFIG['model']['name']), 
            providers=['CPUExecutionProvider'],
            sess_options=get_session_options()
        )
        _ = sess.run(None, {'x': np.zeros((1, 3, 488, 488), dtype='float32')})
        self.predictor, self.input_tensor, self.output_tensors, self.config = sess, sess.get_inputs()[0], None, None

    def __call__(self, img):
        starttime = time.time()
        ori_im = img.copy()
        data = {'image': img}
        data = transform(data, self.preprocess_op)
        img = data[0]
        if img is None:
            return None, 0
        img = np.expand_dims(img, axis=0)
        img = img.copy()
        input_dict = {}
        input_dict[self.input_tensor.name] = img
        outputs = self.predictor.run(self.output_tensors, input_dict)
        preds = {}
        preds['structure_probs'] = outputs[1]
        preds['loc_preds'] = outputs[0]
        shape_list = np.expand_dims(data[-1], axis=0)
        post_result = self.postprocess_op(preds, [shape_list])

        structure_str_list = post_result['structure_batch_list'][0]
        bbox_list = post_result['bbox_batch_list'][0]
        structure_str_list = structure_str_list[0]
        structure_str_list = [
            '<html>', '<body>', '<table>'
        ] + structure_str_list + ['</table>', '</body>', '</html>']
        elapse = time.time() - starttime
        return (structure_str_list, bbox_list), elapse

def expand(pix, det_box, shape):
    x0, y0, x1, y1 = det_box
    h, w, c = shape
    tmp_x0 = x0 - pix
    tmp_x1 = x1 + pix
    tmp_y0 = y0 - pix
    tmp_y1 = y1 + pix
    x0_ = tmp_x0 if tmp_x0 >= 0 else 0
    x1_ = tmp_x1 if tmp_x1 <= w else w
    y0_ = tmp_y0 if tmp_y0 >= 0 else 0
    y1_ = tmp_y1 if tmp_y1 <= h else h
    return x0_, y0_, x1_, y1_

class TableSystem(object):
    def __init__(self, text_detector=None, text_recognizer=None):
        self.text_detector = text_detector
        self.text_recognizer = text_recognizer
        self.table_structurer = TableStructurer()
        self.match = TableMatch(**TABLE_CONFIG['table_match'])

    def __call__(self, img, return_ocr_result_in_table=False, lang='ch'):
        result = dict()
        time_dict = {'det': 0, 'rec': 0, 'table': 0, 'all': 0, 'match': 0}
        start = time.time()
        structure_res, elapse = self._structure(copy.deepcopy(img))
        result['cell_bbox'] = structure_res[1].tolist()
        time_dict['table'] = elapse

        dt_boxes, rec_res, det_elapse, rec_elapse = self._ocr(
            copy.deepcopy(img), lang)
        time_dict['det'] = det_elapse
        time_dict['rec'] = rec_elapse

        if return_ocr_result_in_table:
            result['boxes'] = [x.tolist() for x in dt_boxes]
            result['rec_res'] = rec_res

        tic = time.time()
        pred_html = self.match(structure_res, dt_boxes, rec_res)
        toc = time.time()
        time_dict['match'] = toc - tic
        result['html'] = pred_html
        end = time.time()
        time_dict['all'] = end - start
        return result, time_dict

    def _structure(self, img):
        structure_res, elapse = self.table_structurer(copy.deepcopy(img))
        return structure_res, elapse

    def _ocr(self, img, lang):
        h, w = img.shape[:2]
        dt_boxes = self.text_detector[lang](copy.deepcopy(img))
        dt_boxes = sorted_boxes(dt_boxes)

        r_boxes = []
        for box in dt_boxes:
            x_min = max(0, box[:, 0].min() - 1)
            x_max = min(w, box[:, 0].max() + 1)
            y_min = max(0, box[:, 1].min() - 1)
            y_max = min(h, box[:, 1].max() + 1)
            box = [x_min, y_min, x_max, y_max]
            r_boxes.append(box)
        dt_boxes = np.array(r_boxes)

        if dt_boxes is None:
            return None, None

        img_crop_list = []
        for i in range(len(dt_boxes)):
            det_box = dt_boxes[i]
            x0, y0, x1, y1 = expand(2, det_box, img.shape)
            text_rect = img[int(y0):int(y1), int(x0):int(x1), :]
            img_crop_list.append(text_rect)
        rec_res = self.text_recognizer[lang](img_crop_list)

        return dt_boxes, rec_res, 0, 0