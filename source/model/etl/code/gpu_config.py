import GPUtil

def get_provider_config():
    if len(GPUtil.getGPUs()):
        provider = [("CUDAExecutionProvider", {"cudnn_conv_algo_search": "HEURISTIC"}), "CPUExecutionProvider"]
        rec_batch_num = 6
        layout_model = 'layout.onnx'
    else:
        provider = ["CPUExecutionProvider"]
        rec_batch_num = 1
        layout_model = 'layout_s.onnx'
    
    return provider, rec_batch_num, layout_model 