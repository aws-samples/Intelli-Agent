MODEL_CONFIGS = {
    'ch': {
        'det': 'det_cn.onnx',
        'rec': 'rec_ch.onnx',
        'dict_path': 'ppocr_keys_v1.txt',
        'character_type': 'ch',
        'use_space_char': True
    },
    'en': {
        'det': 'det_en.onnx',
        'rec': 'rec_en.onnx', 
        'dict_path': 'en_dict.txt',
        'character_type': 'en',
        'use_space_char': True
    },
    'multi': {
        'det': 'det_cn.onnx',
        'rec': 'rec_multi_large.onnx',
        'dict_path': 'keys_en_chs_cht_vi_ja_ko.txt',
        'character_type': 'ch',
        'use_space_char': True
    }
}

LAYOUT_CONFIG = {
    'categories': ['text', 'title', 'figure', 'table'],
    'nms_threshold': 0.15,
    'score_threshold': 0.3,
    'image_size': 640,  # Default image processing size
    'aspect_ratio_threshold': 2  # Max ratio threshold for special handling
}

TABLE_CONFIG = {
    'model': {
        'name': 'table_sim.onnx',
        'session_options': {
            'intra_op_num_threads': 8,
            'execution_mode': 'ORT_SEQUENTIAL',
            'optimization_level': 'ORT_ENABLE_ALL'
        }
    },
    'preprocess': [
        {
            'ResizeTableImage': {
                'max_len': 488
            }
        },
        {
            'NormalizeImage': {
                'std': [0.229, 0.224, 0.225],
                'mean': [0.485, 0.456, 0.406],
                'scale': '1./255.',
                'order': 'hwc'
            }
        },
        {
            'PaddingTableImage': {
                'size': [488, 488]
            }
        },
        {
            'ToCHWImage': None
        },
        {
            'KeepKeys': {
                'keep_keys': ['image', 'shape']
            }
        }
    ],
    'postprocess': {
        'name': 'TableLabelDecode',
        'dict_path': 'table_structure_dict_ch.txt',
        'merge_no_span_structure': True
    },
    'table_match': {
        'filter_ocr_result': True
    }
} 