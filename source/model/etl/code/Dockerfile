FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-gpu-py310-cu118-ubuntu20.04-sagemaker

RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends build-essential wget python3 python3-pip libgomp1 libgl1-mesa-glx libglib2.0-0 \
    && ln -sf python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip \
    && pip install --upgrade pip \
    && pip install wheel setuptools

ARG FUNCTION_DIR="/opt/ml/code"
RUN python -m pip install paddlepaddle-gpu==2.5.2 -i https://mirror.baidu.com/pypi/simple
RUN pip install markdownify flask gevent
RUN pip install "paddleocr>=2.6.0.3" 
# # Lite version
RUN ln -s /usr/lib/x86_64-linux-gnu/libcudnn.so.8 /usr/lib/libcudnn.so  
RUN ln -s /usr/local/cuda-11.8/targets/x86_64-linux/lib/libcublas.so.11 /usr/lib/libcublas.so

ADD / ${FUNCTION_DIR}/

#ARG LAYOUT_MODEL_URL="https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/ai-solution-kit/layout-analysis/0.1.0"
ARG LAYOUT_MODEL_URL="https://xiaotih.seal.ac.cn"
RUN wget -c $LAYOUT_MODEL_URL/yolox_l_mix.onnx -O ${FUNCTION_DIR}/weight/picodet_lcnet_x1_0_fgd_layout_cdla_infer/yolox_l_mix.onnx

RUN pip3 install -r ${FUNCTION_DIR}/requirements.txt

WORKDIR ${FUNCTION_DIR}
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PYTHONIOENCODING="utf8"

# Command can be overwritten by providing a different command in the template directly.
ENTRYPOINT ["python", "sm_predictor.py"]