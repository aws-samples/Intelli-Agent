class ModelConfig:
    """模型配置管理类"""
    
    LANG_CONFIGS = {
        'ch': {
            'det': {
                'model': 'det_cn.onnx',
                'postprocess': {
                    'name': 'DBPostProcess',
                    'thresh': 0.1,
                    'box_thresh': 0.1,
                    'max_candidates': 1000,
                    'unclip_ratio': 1.5,
                    'use_dilation': False,
                    'score_mode': 'fast',
                    'box_type': 'quad'
                }
            },
            'rec': {
                'model': 'rec_ch.onnx',
                'dict_path': 'ppocr_keys_v1.txt',
                'postprocess': {
                    'name': 'CTCLabelDecode',
                    'character_type': 'ch',
                    'use_space_char': True
                }
            }
        },
        'en': {
            'det': {
                'model': 'det_en.onnx',
                'postprocess': {
                    'name': 'DBPostProcess',
                    'thresh': 0.1,
                    'box_thresh': 0.1,
                    'max_candidates': 1000,
                    'unclip_ratio': 1.5,
                    'use_dilation': False,
                    'score_mode': 'fast', 
                    'box_type': 'quad'
                }
            },
            'rec': {
                'model': 'rec_en.onnx',
                'dict_path': 'en_dict.txt',
                'postprocess': {
                    'name': 'CTCLabelDecode',
                    'use_space_char': True
                }
            }
        }
    }

    @classmethod
    def get_model_path(cls, lang, model_type):
        """获取模型路径"""
        return os.path.join(
            os.environ['MODEL_PATH'],
            cls.LANG_CONFIGS[lang][model_type]['model']
        )

    @classmethod 
    def get_dict_path(cls, lang):
        """获取字典路径"""
        return os.path.join(
            os.environ['MODEL_PATH'],
            cls.LANG_CONFIGS[lang]['rec']['dict_path']
        )

    @classmethod
    def get_postprocess_config(cls, lang, model_type):
        """获取后处理配置"""
        return cls.LANG_CONFIGS[lang][model_type]['postprocess'] 