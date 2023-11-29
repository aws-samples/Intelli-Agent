FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04

RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends build-essential wget python3 python3-pip libgomp1 libgl1-mesa-glx libglib2.0-0 \
    && ln -sf python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip \
    && pip install --upgrade pip \
    && pip install wheel setuptools

RUN apt install unzip

ARG FUNCTION_DIR="/opt/ml/code"
RUN python -m pip install paddlepaddle-gpu==2.4.2.post117 -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html
RUN pip install markdownify flask gevent
RUN pip install "paddleocr>=2.6.0.3" "paddleclas>=2.4.3"
# Lite version
RUN ln -s /usr/lib/x86_64-linux-gnu/libcudnn.so.8 /usr/lib/libcudnn.so  
RUN ln -s /usr/local/cuda-11.7/targets/x86_64-linux/lib/libcublas.so.11 /usr/lib/libcublas.so
ADD / ${FUNCTION_DIR}/

RUN pip3 install -r ${FUNCTION_DIR}/requirements.txt

RUN unzip ${FUNCTION_DIR}/weight.zip -d ${FUNCTION_DIR}/

WORKDIR ${FUNCTION_DIR}
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PYTHONIOENCODING="utf8"

# Command can be overwritten by providing a different command in the template directly.
ENTRYPOINT ["python", "sm_predictor.py"]