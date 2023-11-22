FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-gpu-py310-cu118-ubuntu20.04-sagemaker

RUN apt update \
    && apt install -y --no-install-recommends wget python3 python3-pip \
    && ln -sf python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip \
    && pip install --upgrade pip \
    && pip install wheel setuptools

RUN apt-get install -y poppler-utils

ARG FUNCTION_DIR="/opt/ml/code"
ADD / ${FUNCTION_DIR}/

RUN pip3 install -r ${FUNCTION_DIR}/requirements.txt
RUN pip3 install flask gevent
RUN pip3 uninstall -y onnxruntime && pip3 install onnxruntime-gpu
RUN pip3 uninstall -y unstructured && pip3 install ${FUNCTION_DIR}/unstructured-0.11.0-py3-none-any.whl

ARG MODEL_DIR="/opt/ml/model"
ARG MODEL_URL="https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/ai-solution-kit/infer-ocr-model/standard"
ARG MODEL_VERSION="v1.0.0"
RUN mkdir -p ${MODEL_DIR}/ocr_model
RUN wget -c $MODEL_URL/$MODEL_VERSION/classifier.onnx -O ${MODEL_DIR}/ocr_model/classifier.onnx
RUN wget -c $MODEL_URL/$MODEL_VERSION/det_standard.onnx -O ${MODEL_DIR}/ocr_model/det_standard.onnx
RUN wget -c $MODEL_URL/$MODEL_VERSION/keys_v1.txt -O ${MODEL_DIR}/ocr_model/keys_v1.txt
RUN wget -c $MODEL_URL/$MODEL_VERSION/rec_standard.onnx -O ${MODEL_DIR}/ocr_model/rec_standard.onnx

WORKDIR ${FUNCTION_DIR}
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PYTHONIOENCODING="utf8"

# Command can be overwritten by providing a different command in the template directly.
ENTRYPOINT ["python", "sm_predictor.py"]